# State-of-the-Art Agentic Planning with LLMs

> A technical analysis covering architecture, domain knowledge sourcing, known limits,
> adaptability, and a comparison with traditional workflow management systems.
>
> Last updated: May 2026

---

## Table of Contents

1. [What Is an LLM Agent?](#1-what-is-an-llm-agent)
2. [How a Pure LLM Becomes a Problem-Solver](#2-how-a-pure-llm-becomes-a-problem-solver)
3. [Sourcing Domain Knowledge](#3-sourcing-domain-knowledge)
4. [Limits of Agentic Systems](#4-limits-of-agentic-systems)
5. [Flexibility and Handling Unforeseen Situations](#5-flexibility-and-handling-unforeseen-situations)
6. [Agents vs. Traditional Workflow Management Systems](#6-agents-vs-traditional-workflow-management-systems)
7. [References](#7-references)

---

## 1. What Is an LLM Agent?

A **language agent** is a system that uses one or more large language models (LLMs)
as its reasoning core and wraps that core with memory, tools, and a
decision loop so that it can pursue multi-step goals rather than just answering
individual queries.

The term encompasses a spectrum from simple augmented chatbots to fully autonomous
systems that browse the web, write and execute code, call APIs, and coordinate
with other agents. The canonical cognitive architecture, described in the 2023
**CoALA** survey [[1]](#ref1), decomposes any language agent into four modules:

| Module | Role |
|---|---|
| **Parametric memory** | Knowledge baked into the LLM weights during pre-training |
| **External memory** | Databases, vector stores, documents retrieved at runtime |
| **Action space** | Tool calls, code execution, web retrieval, file I/O, API calls |
| **Decision procedure** | The loop that decides *when* to act, *which* action to take, and *when* to stop |

The decision procedure is where *planning* lives.

---

## 2. How a Pure LLM Becomes a Problem-Solver

A raw, pre-trained LLM predicts the next token left-to-right. It has no
persistent state, no ability to call external services, and no mechanism to
back up and try again. Several orthogonal augmentations transform it into an agent.

### 2.1 Prompting Strategies that Unlock Reasoning

**Chain-of-Thought (CoT)** prompting [[3]](#ref3) asks the model to emit intermediate
reasoning steps before the final answer. This simple change dramatically improves
performance on arithmetic, commonsense, and symbolic tasks because the model
allocates extra computation (tokens) to work out sub-problems sequentially.

**Tree of Thoughts (ToT)** [[4]](#ref4) generalises CoT from a linear chain to a
search tree. The agent generates *multiple* candidate reasoning paths, self-evaluates
each with a scoring prompt, and pursues the most promising branch via breadth-first
or depth-first search. On tasks that require genuine lookahead—such as the
"Game of 24" puzzle—GPT-4 + CoT solves 4 % of instances while GPT-4 + ToT solves
74 %. ToT is the first architecture to formally introduce **backtracking** into
LLM inference.

**Reflection / self-critique** (Reflexion, self-refine): the model is prompted to
critique its own output and revise it, effectively running multiple passes of
refinement without any external verifier.

**Extended thinking / long-chain-of-thought**: newer RL-trained reasoning models
(o1, DeepSeek-R1, Kimi k1.5 [[12]](#ref12)) learn to emit extensive internal
reasoning tokens before outputting an answer. This moves the search from
prompt engineering to learned behaviour.

### 2.2 Tool Use (Grounding in the Real World)

The **ReAct** framework [[2]](#ref2) interleaves *reasoning traces* with *actions*
in a tight loop: the agent writes a thought, issues a tool call (e.g., Wikipedia
lookup), observes the result, writes another thought, and so on. This breaks the
hallucination–error-propagation spiral that afflicts pure chain-of-thought by
grounding each reasoning step in real, fresh information.

Canonical tool types:
- **Search / retrieval** (web, vector DB, SQL)
- **Code execution** (Python REPL, shell)
- **API calls** (REST endpoints, database writes)
- **File I/O** (read/write workspace files)
- **Sub-agent invocation** (spawning specialist agents)

**HuggingGPT** [[9]](#ref9) pushes tool use further: the LLM acts as a
*controller* that plans which specialised AI models (image segmentation, speech
synthesis, OCR, …) to invoke, chains their outputs, and synthesises a final
answer. The LLM contributes orchestration and language understanding; the
specialised models contribute capabilities the LLM lacks natively.

### 2.3 Memory Systems

| Memory type | Storage medium | Typical use |
|---|---|---|
| Sensory (in-context) | KV-cache / context window | Current task, recent observations |
| Short-term episodic | External scratchpad file / DB | Intermediate results across turns |
| Semantic (parametric) | Model weights | World knowledge, language skills |
| Procedural (skills) | Prompt library, fine-tuned weights | Recurring task patterns |
| Long-term episodic | Vector DB + retrieval | Past episodes retrieved by similarity |

The CoALA taxonomy [[1]](#ref1) maps these to classical cognitive architectures
(SOAR, ACT-R), arguing that the engineering challenge for language agents is
precisely how to manage read/write access across these memory tiers.

### 2.4 Multi-Agent Architectures

Single-agent designs hit context-length limits and struggle with tasks that require
diverse expertise in parallel. Multi-agent systems address this by assigning
specialised roles to different model instances.

**ChatDev** [[8]](#ref8) models a software company: a CEO agent decomposes
requirements, a programmer agent writes code, a tester agent runs unit tests, a
reviewer agent checks style—all communicating via a structured "chat chain". The
key insight is that *communicative dehallucination* (agents challenging each
other's outputs) reduces bugs more effectively than single-agent self-reflection.

The **Masterman et al. survey** [[5]](#ref5) identifies two multi-agent topologies:
- **Hierarchical**: an orchestrator plans and dispatches to specialist sub-agents
  (HuggingGPT, AutoGen supervisor pattern).
- **Flat / peer-to-peer**: agents communicate as equals; consensus or voting
  determines the outcome (LLM debate, society-of-mind patterns).

### 2.5 RL-Trained Reasoning

Reinforcement learning—rewarding the model for producing correct final answers—
allows it to learn *when* to think longer, *when* to backtrack, and *which*
intermediate steps correlate with correctness. Kimi k1.5 [[12]](#ref12) shows that
long-context RL training without Monte Carlo tree search or learned value functions
can match OpenAI o1 performance. This represents a shift from *prompt engineering*
towards *training* as the primary mechanism for agentic planning.

---

## 3. Sourcing Domain Knowledge

A key question for practitioners: *where does the agent learn to cook spaghetti,
or to refactor COBOL?* There are four layered answers.

### 3.1 Pre-training Corpus (Parametric Knowledge)

The LLM absorbs domain knowledge implicitly during pre-training on large text
corpora. A general model trained on Common Crawl, GitHub, arXiv, Wikipedia,
and Stack Overflow will have broad coverage of mainstream programming languages,
cooking recipes, legal concepts, and scientific topics—to the extent that
written text on those topics appeared in the corpus.

This is **quantitatively limited** for niche or proprietary domains:
- COBOL has far less public training data than Python, so parametric knowledge
  degrades sharply for COBOL idioms, JCL, and mainframe-specific patterns.
- Internal company processes, proprietary codebases, or post-training-cutoff
  events do not appear in the weights at all.

### 3.2 Fine-tuning and Domain Adaptation

**Supervised fine-tuning (SFT)** on domain-specific data moves knowledge into the
weights. **Codex** [[11]](#ref11), for example, was GPT-3 fine-tuned on GitHub
code; the result solved 28.8 % of HumanEval Python problems (vs. 0 % for
base GPT-3). The same strategy can be applied to COBOL by fine-tuning on
legacy codebases, JCL documentation, and COBOL refactoring guides.

Trade-offs:
- Fine-tuning is expensive and requires curated data.
- The adapted model may *catastrophically forget* general capabilities unless
  carefully regularised (PEFT, LoRA, QLoRA techniques mitigate this).
- Knowledge is still static after training; it goes stale as the domain evolves.

**RLHF / RLAIF** further shapes the model's behaviour towards domain norms
(e.g., a security-focused code review style, a specific culinary tradition).

### 3.3 Retrieval-Augmented Generation (RAG)

**RAG** [[6]](#ref6) separates *general language capability* (in the weights) from
*specific up-to-date knowledge* (in an external vector database). At inference time
the agent retrieves the most relevant documents and injects them into the context.

Benefits:
- Knowledge can be updated without retraining the LLM.
- Provenance is traceable: the agent cites which document it used.
- Domain specificity is controlled by what you put in the database.

The **RAG Survey** [[7]](#ref7) categorises three generations of RAG:
1. **Naïve RAG**: single retrieval step before generation.
2. **Advanced RAG**: pre-retrieval query rewriting + post-retrieval reranking.
3. **Modular RAG**: retrieval is itself a learned, iterative component; the agent
   decides *when* to retrieve and *what query* to issue.

For domain specificity, RAG allows one LLM to serve multiple domains by switching
out the backing document store—a company's COBOL codebase and documentation,
versus a restaurant's recipe database—without model changes.

### 3.4 System Prompt / In-Context Instructions

The simplest form of domain injection: include rules, style guides, example
code, or a knowledge summary in the system prompt. This is zero-cost but limited
by context window size and degrades in quality for very long prompts.
For shallow domains (a specific API's calling convention, a cuisine's spice profile)
it is often sufficient.

### 3.5 Knowledge Graph Augmentation

**KAM-CoT** [[10]](#ref10) augments chain-of-thought with structured knowledge
graphs (KGs), achieving 93.87 % on ScienceQA vs. 83.99 % for GPT-4. KGs provide
symbolic, verifiable facts that the LLM can traverse, which is valuable in
domains with dense relational structure (pharma, industrial process control,
legal ontologies).

---

## 4. Limits of Agentic Systems

### 4.1 LLMs Are Not Native Planners

**Kambhampati et al.** (ICML 2024) [[13]](#ref13) argue rigorously that
*auto-regressive LLMs cannot, by themselves, do verified planning*. The core
argument:

- Planning requires checking whether a sequence of actions achieves a goal—
  which is *verification*, a fundamentally different computation from
  next-token prediction.
- "Self-verification" prompting (asking the model to check its own plan) does
  not work reliably: the same model that generated a flawed plan will tend to
  validate the same flawed plan.
- Apparent planning success in benchmarks is partially explained by *retrieval
  of similar plans seen during training*, not genuine compositional reasoning.

Their proposed remedy is the **LLM-Modulo Framework**: an LLM generates plan
candidates; an *external symbolic verifier* (a model checker, constraint solver,
or simulation) certifies correctness; feedback loops iterate. This is a
neuro-symbolic architecture, not a pure neural one.

### 4.2 Hallucination and Factual Unreliability

LLMs can generate plausible-sounding but incorrect information. In agentic
settings this is dangerous because:
- A hallucinated API endpoint leads to a failed—or worse, unintended—tool call.
- A hallucinated function name causes a code execution error mid-chain.
- A hallucinated safety property can lead to a plan that violates real-world
  constraints (e.g., in medical or industrial control applications).

RAG and external tool verification reduce but do not eliminate hallucination.

### 4.3 Error Propagation and Irreversibility

In multi-step pipelines, errors compound. Step *k* receives corrupted output from
step *k-1* and its own output is therefore also corrupted. In workflows with
side effects (database writes, file deletions, API calls), early mistakes may be
impossible to undo.

### 4.4 Context Window and Long-Horizon Planning

Current LLMs have finite context windows (8 K – 1 M tokens depending on model).
Tasks requiring very long action sequences—such as a multi-week software project—
exceed the window. External memory mitigates this but introduces retrieval noise
and latency.

### 4.5 Latency and Cost

Complex reasoning (ToT, multi-agent debate) generates many tokens and many
serial LLM calls. A single ToT run can cost 10× – 100× more than a single
chain-of-thought run. This makes agentic systems impractical for high-frequency
or low-latency applications unless carefully throttled.

### 4.6 Non-Determinism and Reproducibility

LLM sampling is stochastic. The same input can produce different plans on
different runs. This is incompatible with audit-trail requirements in regulated
industries (finance, medical devices, automotive safety) without additional
determinism controls (temperature 0 + seed, or external verification).

### 4.7 Security: Prompt Injection and Tool Misuse

When an agent consumes external data (web pages, database records), a malicious
actor can embed adversarial instructions ("ignore previous instructions and…")
that hijack the agent's behaviour. In agentic settings with file-write or
network-call capabilities, prompt injection becomes a serious attack surface
that classical software has no equivalent of.

### 4.8 Skill Gaps for Low-Resource Domains

Domains with little representation in training data—COBOL, industrial PLC
programming, rare languages, proprietary protocols—see sharply degraded
parametric knowledge. RAG can compensate but requires a curated knowledge base
that must be built and maintained.

---

## 5. Flexibility and Handling Unforeseen Situations

### 5.1 Where Agents Genuinely Excel

The defining advantage of LLM agents over rule-based systems is their ability to
handle *underspecified* and *novel* situations through language understanding and
world knowledge.

Examples:
- A user asks in natural language what the agent should do next; the agent
  interprets intent without a pre-defined mapping.
- An unexpected error message from a tool is parsed and a recovery strategy
  improvised (ReAct's exception handling [[2]](#ref2)).
- ChatDev agents deviate from their nominal roles when an unusual bug spans the
  boundary between design and implementation [[8]](#ref8).

This flexibility arises because the LLM's world model, trained on diverse text,
gives it broad coverage of *what kinds of things can go wrong* and *what humans
typically do in response*.

### 5.2 The Boundary of Flexibility

Flexibility is bounded by:

| Constraint | Consequence |
|---|---|
| Out-of-distribution situations | The LLM has no analogous training examples; it may confabulate |
| Tasks requiring formal guarantees | Hallucination risk makes hard correctness guarantees impossible without external verification |
| Very long chains | Context drift, error accumulation |
| Physically grounded tasks | The LLM has only textual world knowledge; physical actions require additional sensorimotor models |

The ReAct paper [[2]](#ref2) quantifies this: on ALFWorld (a household task
simulation), ReAct reaches a success rate of 71 % vs. 37 % for pure imitation
learning—impressive, but not 100 %, and the failures cluster around tasks
requiring very specific object-manipulation sequences.

### 5.3 Adaptive Strategies at Runtime

Modern agents use several mechanisms to react to the unexpected:

- **Reflection and retry**: on a tool error, emit a revised thought and retry
  with a corrected parameter.
- **Plan revision**: if a sub-goal turns out to be impossible, re-plan around it.
- **Escalation**: if the agent's confidence falls below a threshold, hand off to
  a human or a more specialised agent.
- **Meta-cognition prompts**: "Before acting, ask: do I have enough information?
  If not, search for it first."

---

## 6. Agents vs. Traditional Workflow Management Systems

### 6.1 What Traditional WfMS Are

Traditional Workflow Management Systems (WfMS)—BPMN engines (Camunda, Activiti),
business process management (SAP BPM, IBM BPM), RPA platforms (UiPath,
Automation Anywhere), and ETL pipelines—encode processes as an explicit directed
graph of activities, transitions, conditions, and roles. Execution follows the
graph deterministically.

### 6.2 Where Agents Win

| Dimension | LLM Agent | Traditional WfMS |
|---|---|---|
| **Input variability** | Handles natural language, unstructured documents, ambiguous intent | Requires structured input conforming to a schema |
| **New task types** | Can generalise to tasks not explicitly programmed | Cannot; new tasks require explicit workflow design |
| **Unstructured exception handling** | Improvises recovery from novel errors | Requires pre-defined exception paths |
| **Cross-domain tasks** | Mixes domains (e.g., look up a regulation, then write the code to enforce it) | Domain knowledge must be explicitly encoded |
| **Iterative refinement** | Natural; the loop is intrinsic | Requires an explicit loop node with a condition |
| **Time to first capability** | Minutes (prompt engineering) | Days to weeks (BPMN modelling, testing) |

### 6.3 Where Traditional WfMS Win

| Dimension | LLM Agent | Traditional WfMS |
|---|---|---|
| **Correctness guarantees** | Probabilistic; hallucinations possible | Deterministic; if the graph is correct, execution is correct |
| **Auditability** | Difficult; reasoning is opaque | Full audit trail; every transition is logged |
| **Compliance** | Hard to certify (non-deterministic) | Certifiable against regulatory standards (ISO 9001, GDPR process records) |
| **Performance / cost** | High token cost, high latency | Near-zero per-step cost; microsecond transitions |
| **Concurrency management** | Poor native support; race conditions in multi-agent writes | First-class primitives (fork, join, mutex, transactions) |
| **Long-running processes** | Context window limitation | Handles months-long processes natively (durable execution) |
| **Integration with enterprise systems** | Requires custom tool wrappers | Native connectors for SAP, Oracle, Salesforce, etc. |
| **Deterministic repeatability** | Stochastic unless temperature=0 | Identical inputs produce identical outputs |
| **Operator visibility** | Black-box; hard to monitor | BPMN diagrams serve as live execution monitors |

### 6.4 Hybrid Architectures: The Practical Sweet Spot

Most production deployments in 2025–2026 use a **hybrid** strategy:

```
Traditional WfMS                LLM Agent
──────────────────              ─────────────────────────
Durable process state           Interprets free-text input
SLA enforcement                 Handles exception triage
Audit logging                   Writes structured summaries
Compliance checkpoints          Extracts data from documents
Human approval gates            Fills structured forms from NL
Deterministic routing           Routes to human when uncertain
```

In this pattern the WfMS provides the *skeleton* (guaranteed execution, audit,
SLAs) and the LLM agent provides the *intelligence* for steps that involve
language understanding, document processing, or novel decision-making. The LLM's
output is validated (schema check, rules engine, human review) before being
written into the WfMS state—instantiating the LLM-Modulo pattern [[13]](#ref13)
at the process level.

---

## 7. References

<a id="ref1"></a>**[1]** Sumers, T. R., Yao, S., Narasimhan, K., & Griffiths, T. L. (2024).
*Cognitive Architectures for Language Agents (CoALA).*
TMLR. https://arxiv.org/abs/2309.02427

<a id="ref2"></a>**[2]** Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., & Cao, Y. (2023).
*ReAct: Synergizing Reasoning and Acting in Language Models.*
ICLR 2023. https://arxiv.org/abs/2210.03629

<a id="ref3"></a>**[3]** Wei, J., Wang, X., Schuurmans, D., Bosma, M., Chi, E., Le, Q., & Zhou, D. (2022).
*Chain-of-Thought Prompting Elicits Reasoning in Large Language Models.*
NeurIPS 2022. https://arxiv.org/abs/2201.11903

<a id="ref4"></a>**[4]** Yao, S., Yu, D., Zhao, J., Shafran, I., Griffiths, T. L., Cao, Y., & Narasimhan, K. (2023).
*Tree of Thoughts: Deliberate Problem Solving with Large Language Models.*
NeurIPS 2023. https://arxiv.org/abs/2305.10601

<a id="ref5"></a>**[5]** Masterman, T., Besen, S., Sawtell, M., & Chao, A. (2024).
*The Landscape of Emerging AI Agent Architectures for Reasoning, Planning, and Tool Calling: A Survey.*
https://arxiv.org/abs/2404.11584

<a id="ref6"></a>**[6]** Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., et al. (2020).
*Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.*
NeurIPS 2020. https://arxiv.org/abs/2005.11401

<a id="ref7"></a>**[7]** Gao, Y., Xiong, Y., Gao, X., Jia, K., Pan, J., et al. (2024).
*Retrieval-Augmented Generation for Large Language Models: A Survey.*
https://arxiv.org/abs/2312.10997

<a id="ref8"></a>**[8]** Qian, C., Liu, W., Liu, H., Chen, N., Dang, Y., et al. (2024).
*ChatDev: Communicative Agents for Software Development.*
ACL 2024. https://arxiv.org/abs/2307.07924

<a id="ref9"></a>**[9]** Shen, Y., Song, K., Tan, X., Li, D., Lu, W., & Zhuang, Y. (2023).
*HuggingGPT: Solving AI Tasks with ChatGPT and its Friends in Hugging Face.*
NeurIPS 2023. https://arxiv.org/abs/2303.17580

<a id="ref10"></a>**[10]** Mondal, D., Modi, S., Panda, S., Singh, R., & Rao, G. S. (2024).
*KAM-CoT: Knowledge Augmented Multimodal Chain-of-Thoughts Reasoning.*
AAAI 2024. https://arxiv.org/abs/2401.12863

<a id="ref11"></a>**[11]** Chen, M., Tworek, J., Jun, H., Yuan, Q., et al. (2021).
*Evaluating Large Language Models Trained on Code (Codex).*
https://arxiv.org/abs/2107.03374

<a id="ref12"></a>**[12]** Kimi Team. (2025).
*Kimi k1.5: Scaling Reinforcement Learning with LLMs.*
https://arxiv.org/abs/2501.12599

<a id="ref13"></a>**[13]** Kambhampati, S., Valmeekam, K., Guan, L., Verma, M., Stechly, K., et al. (2024).
*LLMs Can't Plan, But Can Help Planning in LLM-Modulo Frameworks.*
ICML 2024. https://arxiv.org/abs/2402.01817

<a id="ref14"></a>**[14]** Wang, L., Ma, C., Feng, X., Zhang, Z., Yang, H., et al. (2024).
*A Survey on Large Language Model based Autonomous Agents.*
Frontiers of Computer Science. https://arxiv.org/abs/2308.11432
