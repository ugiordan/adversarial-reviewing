## Unverified External References

When your analysis depends on systems, components, or implementations referenced but not defined in the reviewed document (existing platform services, upstream project capabilities, external APIs, infrastructure behavior):

1. **Flag the dependency**: State explicitly: "This finding depends on [system/component] which is referenced but not defined in the reviewed document."
2. **Do not infer implementation details**: If the document references an external system's behavior without specification, state what the document assumes about it. Note the assumption is unverified. Do not present inferences about external systems as established facts.
3. **Set Confidence: Low** for findings whose severity depends on unverified external system behavior.

A finding built on "external system X works this way" when you're inferring behavior from the document's description rather than verified architecture context is assumption-based. Apply Evidence Requirements: cite the document's claim and note it as unverified.
