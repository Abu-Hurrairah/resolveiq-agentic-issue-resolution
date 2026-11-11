# ResolveIQ — honest 60–90 second Qwen demo

**Preparation:** Install Qwen via `INSTALL_QWEN_WINDOWS.bat`, run Ollama, start ResolveIQ, and make sure the top badge actually reads `Qwen AI online`. Do not show a fake model status or claim Qwen ran if the badge says `Rules fallback`.

1. **0:00–0:10**: Show dashboard. Click **Qwen AI online**. The modal shows Ollama, exact model, and live status.
2. **0:10–0:25**: Click **New issue**, enter a genuine example (e.g., an authentication redirect affecting several users), then **Analyze issue**.
3. **0:25–0:45**: Open analysis. Highlight **Ollama · qwen2.5:3b**, the summary, root-cause uncertainty, retrieved playbooks, and recommended steps.
4. **0:45–1:00**: Click **Approve & assign**. Show created tasks and the Activity log. Explain that no external services are changed.
5. **1:00–1:20**: Stop Ollama, refresh the badge, then create another issue. Show **Rules fallback** and the new issue source **Offline rules · fallback**. Explain the product remains useful offline.

Remember: **Ollama works without internet once the Qwen model is downloaded.** Fallback is for local model outages/missing model, not every internet disconnection.

**Cloud demo:** Render runs offline rules if Ollama isn't installed on the Render server. Never describe a cloud rules demo as a live Qwen demo. You can include a local screen recording of the model path if you genuinely ran it.
