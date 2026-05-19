\# System Limitations



\# Overview



This project intentionally exposes the limitations and reliability challenges of enterprise GenAI systems.



The framework is designed to measure uncertainty rather than hide it.



\---



\# Known Limitations



\## Probabilistic Outputs



LLMs remain non-deterministic systems.



The same prompt may generate different outputs across executions.



\---



\## Judge Bias



LLM-as-a-Judge evaluation may introduce scoring subjectivity and evaluator bias.



\---



\## Grounding Constraints



Some prompts may require KPIs or evidence not explicitly available in source documents.



\---



\## Semantic Similarity Limitations



Semantic similarity scoring does not guarantee factual correctness.



\---



\## Prompt Drift



Prompt behavior may evolve across:



\- model versions,

\- temperature settings,

\- and API updates.



\---



\## Source Quality Dependency



Evaluation quality depends heavily on source-document quality and evidence availability.



\---



\# Enterprise Implication



Enterprise GenAI systems require:



\- continuous monitoring,

\- evaluation,

\- governance,

\- and reliability validation.



Prompt engineering alone is insufficient for operational trustworthiness.

