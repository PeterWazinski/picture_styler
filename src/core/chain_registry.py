"""BuiltinChainRegistry — read operations over the built-in chain catalog.

Chains are read-only from the application's perspective; the catalog
is only written by the developer tooling (add_style_chain notebook).

Typical usage::

    registry = BuiltinChainRegistry(catalog_path=Path("style_chains/catalog.json"))
    for chain in registry.list_chains():
        print(chain.name)

    invalid = registry.validate_styles(style_registry)
    for chain_id, missing in invalid.items():
        logger.warning("Chain '%s' missing styles: %s", chain_id, missing)
"""
from __future__ import annotations

import logging
from pathlib import Path

from src.core.chain_models import BuiltinChainModel, ChainStore

logger: logging.Logger = logging.getLogger(__name__)


class ChainNotFoundError(KeyError):
    """Raised when a requested chain ID is not in the catalog."""


class BuiltinChainRegistry:
    """In-memory built-in chain catalog backed by JSON files.

    System chains are loaded from *catalog_path* (never written at runtime).
    User chains are loaded from *user_catalog_path* if provided, and can be
    mutated via :meth:`add_user_chain` and :meth:`remove_chain`.

    Args:
        catalog_path:      Path to the system JSON catalog (read-only at runtime).
        user_catalog_path: Optional path to the user JSON catalog (read/write).
    """

    def __init__(
        self,
        catalog_path: Path,
        user_catalog_path: Path | None = None,
    ) -> None:
        self._store: ChainStore = ChainStore(catalog_path)
        self._user_store: ChainStore | None = (
            ChainStore(user_catalog_path) if user_catalog_path is not None else None
        )
        self._chains: list[BuiltinChainModel] | None = None       # lazy-loaded system
        self._user_chains: list[BuiltinChainModel] | None = None  # lazy-loaded user

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_loaded(self) -> None:
        if self._chains is None:
            self._chains = self._store.load()

    def _ensure_user_loaded(self) -> None:
        if self._user_store is not None and self._user_chains is None:
            self._user_chains = self._user_store.load()

    @property
    def _catalog(self) -> list[BuiltinChainModel]:
        self._ensure_loaded()
        assert self._chains is not None
        return self._chains

    @property
    def _user_catalog(self) -> list[BuiltinChainModel]:
        self._ensure_user_loaded()
        return self._user_chains or []

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def list_chains(self) -> list[BuiltinChainModel]:
        """Return all chains (system + user) sorted alphabetically by name."""
        return sorted(self._catalog + self._user_catalog, key=lambda c: c.name.casefold())

    def get(self, chain_id: str) -> BuiltinChainModel:
        """Return the chain with *chain_id*, or raise :exc:`ChainNotFoundError`."""
        for chain in self._catalog:
            if chain.id == chain_id:
                return chain
        raise ChainNotFoundError(f"Chain '{chain_id}' not found in the catalog.")

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_styles(
        self,
        style_registry: "StyleRegistry",  # type: ignore[name-defined]  # noqa: F821
        root: Path | None = None,
    ) -> dict[str, list[str]]:
        """Check that every step in every chain references a known style.

        Args:
            style_registry: The application's :class:`~src.core.registry.StyleRegistry`.
            root:           Project root used to resolve relative ``chain_path``
                            values.  When *None* the current working directory
                            is used.

        Returns:
            A ``dict`` mapping ``chain_id`` → ``[missing_style_name, ...]``.
            Only chains with at least one missing style are included.
            An empty dict means all chains are valid.
        """
        from src.core.style_chain_schema import load_style_chain

        if root is None:
            root = Path.cwd()

        invalid: dict[str, list[str]] = {}
        for chain in self._catalog:
            yml_path = chain.chain_path_resolved(root)
            if not yml_path.exists():
                logger.warning(
                    "Built-in chain '%s': YAML not found at %s", chain.id, yml_path
                )
                invalid[chain.id] = [f"<missing file: {yml_path.name}>"]
                continue
            try:
                sc = load_style_chain(yml_path)
            except ValueError as exc:
                logger.warning(
                    "Built-in chain '%s': invalid YAML: %s", chain.id, exc
                )
                invalid[chain.id] = [f"<invalid YAML: {exc}>"]
                continue
            missing = [
                step.style
                for step in sc.steps
                if style_registry.find_by_name(step.style) is None
            ]
            if missing:
                logger.warning(
                    "Built-in chain '%s' references unknown styles: %s",
                    chain.id,
                    missing,
                )
                invalid[chain.id] = missing
        return invalid

    # ------------------------------------------------------------------
    # Mutation (user chains only)
    # ------------------------------------------------------------------

    def add_user_chain(self, chain: BuiltinChainModel) -> None:
        """Add a user chain to the user catalog.

        Raises :exc:`RuntimeError` if no user catalog path was provided.
        Raises :exc:`ValueError` if a chain with the same id already exists.
        """
        if self._user_store is None:
            raise RuntimeError(
                "BuiltinChainRegistry was created without a user_catalog_path."
            )
        self._ensure_user_loaded()
        assert self._user_chains is not None
        if any(c.id == chain.id for c in self._user_chains + self._catalog):
            raise ValueError(f"Chain id '{chain.id}' already exists.")
        user_chain = BuiltinChainModel(
            id=chain.id, name=chain.name, chain_path=chain.chain_path,
            preview_path=chain.preview_path, description=chain.description,
            step_count=chain.step_count, tags=chain.tags, is_builtin=False,
        )
        self._user_store.add_chain(user_chain)
        self._user_chains.append(user_chain)
        logger.debug("User chain added: %s", chain.id)

    def remove_chain(self, chain_id: str) -> None:
        """Remove a user chain by id.

        Raises :exc:`ValueError` if *chain_id* belongs to a system chain.
        Raises :exc:`KeyError` if *chain_id* is not found.
        """
        if any(c.id == chain_id for c in self._catalog):
            raise ValueError(
                f"Cannot remove system chain '{chain_id}'."
            )
        if self._user_store is None:
            raise RuntimeError(
                "BuiltinChainRegistry was created without a user_catalog_path."
            )
        self._ensure_user_loaded()
        assert self._user_chains is not None
        if not any(c.id == chain_id for c in self._user_chains):
            raise KeyError(f"User chain '{chain_id}' not found.")
        self._user_store.remove_chain(chain_id)
        self._user_chains = [c for c in self._user_chains if c.id != chain_id]
        logger.debug("User chain removed: %s", chain_id)
