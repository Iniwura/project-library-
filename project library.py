# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
import json
from genlayer import *


class ProjectLibrary(gl.Contract):
    """
    On-chain library of GenLayer ecosystem projects.
    Anyone can submit a project. The AI auto-categorises,
    summarises, and scores it by fetching the live URL.
    Community can upvote. Owner can feature/remove.
    """

    # ── Storage ──────────────────────────────────────────────
    projects_json:  str   # {id: {name,desc,url,github,...}}
    project_count:  u64
    votes_json:     str   # {project_id: [address,...]}
    owner:          str

    CATEGORIES = [
        "DeFi", "Gaming", "NFT", "DAO", "Identity",
        "Prediction Market", "Social", "Infrastructure",
        "AI Agent", "Other"
    ]

    def __init__(self):
        self.owner         = str(gl.message.sender_address).lower().strip()
        self.projects_json = "{}"
        self.votes_json    = "{}"
        self.project_count = u64(0)

    # ── Helpers ──────────────────────────────────────────────
    def _projects(self)  -> dict: return json.loads(self.projects_json)
    def _votes(self)     -> dict: return json.loads(self.votes_json)
    def _addr(self)      -> str:  return str(gl.message.sender_address).lower().strip()
    def _save_projects(self, d):  self.projects_json = json.dumps(d)
    def _save_votes(self, d):     self.votes_json    = json.dumps(d)

    # ── Views ─────────────────────────────────────────────────

    @gl.public.view
    def get_project(self, project_id: int) -> str:
        projects = self._projects()
        p = projects.get(str(project_id))
        if not p:
            return "NOT_FOUND"
        votes = self._votes()
        p["votes"] = len(votes.get(str(project_id), []))
        return json.dumps(p)

    @gl.public.view
    def get_all_projects(self) -> str:
        count = int(self.project_count)
        if count == 0:
            return "[]"
        projects = self._projects()
        votes    = self._votes()
        result   = []
        for i in range(count):
            p = projects.get(str(i))
            if p:
                p["votes"] = len(votes.get(str(i), []))
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
        votes = self._votes()
        addr  = address.lower().strip()
        return str(addr in votes.get(str(project_id), []))

    # ── Writes ────────────────────────────────────────────────

    @gl.public.write
    def submit_project(self, name: str, description: str,
                       url: str, github: str, contract_addr: str):
        """
        Submit a project to the library. AI fetches the URL,
        auto-categorises it, writes a one-line summary, and
        gives it an innovation score (1-10).
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
            # Fetch the project URL for context (optional — skip if blank)
            context = ""
            if url and url.startswith("http"):
                try:
                    raw = gl.nondet.web.render(url, mode="text")
                    context = raw[:2000]
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
                "Analyse a GenLayer project submission and return a JSON "
                "with category, summary, score (1-10), and tags."
            ),
            criteria=(
                "Valid JSON with 'category' (from the provided list), "
                "'summary' (string ≤120 chars), 'score' (integer 1-10), "
                "and 'tags' (list of up to 5 short strings). "
                "Score and category must be realistic for the project described."
            ),
        )

        try:
            ai = json.loads(str(raw))
        except Exception:
            ai = {"category": "Other", "summary": description[:120], "score": 5, "tags": []}

        projects = self._projects()
        projects[str(pid)] = {
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
        }
        self._save_projects(projects)
        self.project_count = u64(pid + 1)

    @gl.public.write
    def upvote(self, project_id: int):
        """Toggle upvote — call once to vote, again to unvote."""
        projects = self._projects()
        pid      = str(project_id)
        if pid not in projects:
            raise Exception("Project not found")
        if projects[pid].get("removed"):
            raise Exception("Project has been removed")

        addr  = self._addr()
        votes = self._votes()
        if pid not in votes:
            votes[pid] = []

        if addr in votes[pid]:
            votes[pid].remove(addr)
        else:
            votes[pid].append(addr)

        self._save_votes(votes)

    @gl.public.write
    def feature_project(self, project_id: int, featured: bool):
        """Owner only — mark a project as featured."""
        if self._addr() != self.owner:
            raise Exception("Owner only")
        projects = self._projects()
        pid      = str(project_id)
        if pid not in projects:
            raise Exception("Project not found")
        projects[pid]["featured"] = featured
        self._save_projects(projects)

    @gl.public.write
    def remove_project(self, project_id: int):
        """Owner only — soft-remove a project."""
        if self._addr() != self.owner:
            raise Exception("Owner only")
        projects = self._projects()
        pid      = str(project_id)
        if pid not in projects:
            raise Exception("Project not found")
        projects[pid]["removed"] = True
        self._save_projects(projects)
