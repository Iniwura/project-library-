# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
import json
from genlayer import *


class ProjectLibrary(gl.Contract):
    """
    On-chain library of GenLayer ecosystem projects.
    Anyone can submit. AI auto-categorises, summarises, and scores
    by fetching the live URL. Community can upvote. Owner can feature/remove.
    Upgraded: TreeMap storage, web.get(), validate-only criteria.
    """

    projects:      TreeMap[str, str]   # project_id -> json(project)
    votes:         TreeMap[str, str]   # project_id -> json([addr, ...])
    project_count: u64
    owner:         str

    CATEGORIES = [
        "DeFi", "Gaming", "NFT", "DAO", "Identity",
        "Prediction Market", "Social", "Infrastructure",
        "AI Agent", "Other"
    ]

    def __init__(self):
        self.owner         = str(gl.message.sender_address).lower().strip()
        self.project_count = u64(0)
        root = gl.storage.Root.get()
        root.upgraders.get().append(gl.message.sender_address)

    # ── Helpers ──────────────────────────────────────────────
    def _addr(self) -> str: return str(gl.message.sender_address).lower().strip()

    def _get_project(self, pid: str) -> dict:
        raw = self.projects.get(pid, None)
        if raw is None:
            raise Exception("Project not found")
        return json.loads(raw)

    def _save_project(self, pid: str, p: dict):
        self.projects[pid] = json.dumps(p)

    def _get_votes(self, pid: str) -> list:
        raw = self.votes.get(pid, None)
        if raw is None:
            return []
        return json.loads(raw)

    def _save_votes(self, pid: str, v: list):
        self.votes[pid] = json.dumps(v)

    # ── Views ─────────────────────────────────────────────────

    @gl.public.view
    def get_project(self, project_id: int) -> str:
        pid = str(project_id)
        raw = self.projects.get(pid, None)
        if raw is None:
            return "NOT_FOUND"
        p = json.loads(raw)
        p["votes"] = len(self._get_votes(pid))
        return json.dumps(p)

    @gl.public.view
    def get_all_projects(self) -> str:
        count = int(self.project_count)
        if count == 0:
            return "[]"
        result = []
        for i in range(count):
            pid = str(i)
            raw = self.projects.get(pid, None)
            if raw is None:
                continue
            p = json.loads(raw)
            p["votes"] = len(self._get_votes(pid))
            result.append(p)
        return json.dumps(result)

    @gl.public.view
    def get_project_count(self) -> str:
        return str(int(self.project_count))

    @gl.public.view
    def get_owner(self) -> str:
        return self.owner

    @gl.public.view
    def has_voted(self, project_id: int, address: str) -> str:
        addr = address.lower().strip()
        return str(addr in self._get_votes(str(project_id)))

    # ── Writes ────────────────────────────────────────────────

    @gl.public.write
    def upgrade(self, new_code: bytes) -> None:
        """Push a new version without changing the contract address. Deployer only."""
        root = gl.storage.Root.get()
        code = root.code.get()
        code.truncate()
        code.extend(new_code)

    @gl.public.write
    def submit_project(self, name: str, description: str,
                       url: str, github: str, contract_addr: str):
        """
        Submit a project. AI fetches the URL, auto-categorises,
        writes a one-line summary, and gives an innovation score (1-10).
        """
        name        = name.strip()
        description = description.strip()
        url         = url.strip()
        github      = github.strip()

        if not name:
            raise Exception("Project name required")
        if len(name) > 80:
            raise Exception("Name too long (max 80 chars)")
        if len(description) > 500:
            raise Exception("Description too long (max 500 chars)")

        submitter = self._addr()
        pid       = int(self.project_count)
        cats_str  = ", ".join(self.CATEGORIES)

        def analyse_project():
            context = ""
            if url and url.startswith("http"):
                try:
                    response = gl.nondet.web.get(url)
                    context  = response.body.decode("utf-8", errors="replace")[:2000]
                except Exception:
                    context = ""

            prompt = (
                "You are reviewing a GenLayer ecosystem project submission.\n\n"
                "PROJECT NAME: " + name + "\n"
                "DESCRIPTION: " + description + "\n"
                "URL: " + (url or "none") + "\n"
                "GITHUB: " + (github or "none") + "\n"
                "LIVE CONTEXT:\n" + context + "\n\n"
                "AVAILABLE CATEGORIES: " + cats_str + "\n\n"
                "Return ONLY a JSON object in this exact shape:\n"
                '{"category": "<one from the list>", '
                '"summary": "<one sentence, max 120 chars>", '
                '"score": <integer 1-10>, '
                '"tags": ["<tag1>", "<tag2>", "<tag3>"]}\n\n'
                "Score criteria: 1-3 basic/tutorial, 4-6 solid dApp, "
                "7-8 innovative use of GenLayer AI, 9-10 ecosystem-defining.\n"
                "No other text. Return only the JSON."
            )
            result = gl.nondet.exec_prompt(prompt, response_format="json")
            cat    = result.get("category", "Other")
            if cat not in self.CATEGORIES:
                cat = "Other"
            summary = str(result.get("summary", description[:120]))[:120]
            score   = max(1, min(10, int(result.get("score", 5))))
            tags    = result.get("tags", [])
            if not isinstance(tags, list):
                tags = []
            tags = [str(t)[:30] for t in tags[:5]]
            return json.dumps({
                "category": cat,
                "summary":  summary,
                "score":    score,
                "tags":     tags,
            }, sort_keys=True)

        raw = gl.eq_principle.prompt_non_comparative(
            analyse_project,
            task=(
                "Analyse a GenLayer project submission and return JSON "
                "with category, summary, score (1-10), and tags."
            ),
            criteria=(
                "Validate format only - do NOT evaluate quality. "
                "Accept if: (1) valid JSON object, (2) 'category' is one of the "
                "provided categories, (3) 'summary' is a non-empty string ≤120 chars, "
                "(4) 'score' is an integer 1-10, (5) 'tags' is a list of strings."
            ),
        )

        try:
            ai = json.loads(str(raw))
        except Exception:
            ai = {"category": "Other", "summary": description[:120], "score": 5, "tags": []}

        self._save_project(str(pid), {
            "id":            pid,
            "name":          name,
            "description":   description,
            "url":           url,
            "github":        github,
            "contract_addr": contract_addr.strip(),
            "submitter":     submitter,
            "category":      ai.get("category", "Other"),
            "summary":       ai.get("summary", description[:120]),
            "score":         ai.get("score", 5),
            "tags":          ai.get("tags", []),
            "featured":      False,
            "removed":       False,
        })
        self.project_count = u64(pid + 1)

    @gl.public.write
    def upvote(self, project_id: int):
        """Toggle upvote — call once to vote, again to unvote."""
        pid = str(project_id)
        raw = self.projects.get(pid, None)
        if raw is None:
            raise Exception("Project not found")
        p = json.loads(raw)
        if p.get("removed"):
            raise Exception("Project has been removed")

        addr  = self._addr()
        v     = self._get_votes(pid)
        if addr in v:
            v.remove(addr)
        else:
            v.append(addr)
        self._save_votes(pid, v)

    @gl.public.write
    def feature_project(self, project_id: int, featured: bool):
        """Owner only — mark a project as featured."""
        if self._addr() != self.owner:
            raise Exception("Owner only")
        pid = str(project_id)
        p   = self._get_project(pid)
        p["featured"] = featured
        self._save_project(pid, p)

    @gl.public.write
    def remove_project(self, project_id: int):
        """Owner only — soft-remove a project."""
        if self._addr() != self.owner:
            raise Exception("Owner only")
        pid = str(project_id)
        p   = self._get_project(pid)
        p["removed"] = True
        self._save_project(pid, p)
