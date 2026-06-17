# GenLayer Project Library

> AI-scored community directory for the GenLayer ecosystem

Every dApp, Intelligent Contract, and tool built on GenLayer — submitted by the community, automatically scored by AI, stored on-chain.

**Contract:** `0xFc6874768B6cAF8CAD6CD937A476454D53062890`

---

## What it does

Submit any GenLayer project. The Intelligent Contract fetches your live URL, reads it, and automatically:

- **Categorises** it across 10 categories (DeFi, Gaming, NFT, DAO, Identity, Prediction Market, Social, Infrastructure, AI Agent, Other)
- **Summarises** it in one sentence
- **Scores** it 1-10 based on innovation and use of GenLayer primitives

Results are stored permanently on-chain. Community members vote on projects. No human curator, no approval queue.

---

## AI scoring

Uses `prompt_non_comparative` consensus — leader validator fetches the URL and runs the full analysis once, other validators verify the output format and realism:

```python
def analyse_project():
    raw = gl.nondet.web.render(url, mode="text")
    context = raw[:2000]
    prompt = (
        "Review this GenLayer project. Return JSON:\n"
        '{"category": "...", "summary": "...", "score": 1-10, "tags": [...]}\n\n'
        "Score: 1-3 basic, 4-6 solid dApp, 7-8 innovative GenLayer AI use, "
        "9-10 ecosystem-defining."
    )
    return gl.nondet.exec_prompt(prompt, response_format="json")

result = gl.eq_principle.prompt_non_comparative(analyse_project, ...)
```

---

## Contract methods

| Method | Description |
|--------|-------------|
| `submit_project(name, desc, url, github, contract_addr)` | Submit a project — AI fetches URL, scores and categorises |
| `upvote(project_id)` | Toggle upvote — on-chain per wallet |
| `feature_project(project_id, featured)` | Owner only — mark as featured |
| `remove_project(project_id)` | Owner only — soft remove |
| `get_all_projects()` | JSON array of all projects with votes |
| `get_project(project_id)` | Single project lookup |
| `has_voted(project_id, address)` | Check if address has voted |
| `get_project_count()` | Total number of submissions |
| `get_owner()` | Contract owner address |

---

## Repo structure

```
gl-library/
├── project_library.py       # Intelligent Contract
├── project_library_site.html # Frontend (single file)
└── README.md
```

---

### GenLayer Bradbury network
```
RPC:      https://rpc-bradbury.genlayer.com
Chain ID: 4221
Currency: GEN
Explorer: https://explorer-bradbury.genlayer.com
```



---

Built by [@iniwuraakuru](https://github.com/iniwuraakuru) · GenLayer Bradbury Builder Program
