"""
Skill Database for Zecpath ATS Engine.
Contains the master skill registry, stack definitions, and level indicators.
"""

from typing import TypedDict

class SkillEntry(TypedDict):
    variants: list[str]
    category: str
    is_technical: bool


MASTER_SKILL_DB: dict[str, SkillEntry] = {

    # ─── PROGRAMMING ───────────────────────────────────────────────────────────
    "Python": {
        "variants": ["python", "py", "python3"],
        "category": "programming",
        "is_technical": True,
    },
    "JavaScript": {
        "variants": ["javascript", "js"],
        "category": "programming",
        "is_technical": True,
    },
    "TypeScript": {
        "variants": ["typescript", "ts"],
        "category": "programming",
        "is_technical": True,
    },
    "Java": {
        "variants": ["java"],
        "category": "programming",
        "is_technical": True,
    },
    "C++": {
        "variants": ["c++", "cpp"],
        "category": "programming",
        "is_technical": True,
    },
    "C#": {
        "variants": ["c#", "csharp", "c sharp"],
        "category": "programming",
        "is_technical": True,
    },
    "R": {
        "variants": ["r"],
        "category": "programming",
        "is_technical": True,
    },
    "SQL": {
        "variants": ["sql"],
        "category": "programming",
        "is_technical": True,
    },
    "Go": {
        "variants": ["go", "golang"],
        "category": "programming",
        "is_technical": True,
    },
    "Rust": {
        "variants": ["rust"],
        "category": "programming",
        "is_technical": True,
    },
    "PHP": {
        "variants": ["php"],
        "category": "programming",
        "is_technical": True,
    },
    "Swift": {
        "variants": ["swift"],
        "category": "programming",
        "is_technical": True,
    },

    # ─── FRAMEWORKS & LIBRARIES ────────────────────────────────────────────────
    "Django": {
        "variants": ["django"],
        "category": "framework",
        "is_technical": True,
    },
    "Flask": {
        "variants": ["flask"],
        "category": "framework",
        "is_technical": True,
    },
    "FastAPI": {
        "variants": ["fastapi", "fast api"],
        "category": "framework",
        "is_technical": True,
    },
    "React": {
        "variants": ["react", "reactjs", "react.js"],
        "category": "framework",
        "is_technical": True,
    },
    "Angular": {
        "variants": ["angular", "angularjs"],
        "category": "framework",
        "is_technical": True,
    },
    "Vue": {
        "variants": ["vue", "vuejs", "vue.js"],
        "category": "framework",
        "is_technical": True,
    },
    "Node": {
        "variants": ["node", "nodejs", "node.js"],
        "category": "framework",
        "is_technical": True,
    },
    "Express": {
        "variants": ["express", "expressjs", "express.js"],
        "category": "framework",
        "is_technical": True,
    },
    "Spring": {
        "variants": ["spring", "spring boot", "spring framework"],
        "category": "framework",
        "is_technical": True,
    },
    "Laravel": {
        "variants": ["laravel"],
        "category": "framework",
        "is_technical": True,
    },
    "TensorFlow": {
        "variants": ["tensorflow", "tensor flow"],
        "category": "framework",
        "is_technical": True,
    },
    "PyTorch": {
        "variants": ["pytorch", "torch"],
        "category": "framework",
        "is_technical": True,
    },
    "LangChain": {
        "variants": ["langchain", "lang chain"],
        "category": "framework",
        "is_technical": True,
    },
    "LangGraph": {
        "variants": ["langgraph", "lang graph"],
        "category": "framework",
        "is_technical": True,
    },
    "Scikit-learn": {
        "variants": ["scikit-learn", "sklearn", "scikit learn"],
        "category": "framework",
        "is_technical": True,
    },

    # ─── DATABASES ─────────────────────────────────────────────────────────────
    "PostgreSQL": {
        "variants": ["postgresql", "postgres", "postgre sql"],
        "category": "database",
        "is_technical": True,
    },
    "MySQL": {
        "variants": ["mysql", "my sql"],
        "category": "database",
        "is_technical": True,
    },
    "MongoDB": {
        "variants": ["mongodb", "mongo"],
        "category": "database",
        "is_technical": True,
    },
    "SQLite": {
        "variants": ["sqlite", "sqlite3"],
        "category": "database",
        "is_technical": True,
    },
    "Redis": {
        "variants": ["redis"],
        "category": "database",
        "is_technical": True,
    },
    "ChromaDB": {
        "variants": ["chromadb", "chroma db", "chroma"],
        "category": "database",
        "is_technical": True,
    },
    "Elasticsearch": {
        "variants": ["elasticsearch", "elastic search", "elastic"],
        "category": "database",
        "is_technical": True,
    },
    "Oracle": {
        "variants": ["oracle", "oracle db", "oracle database"],
        "category": "database",
        "is_technical": True,
    },

    # ─── CLOUD ─────────────────────────────────────────────────────────────────
    "AWS": {
        "variants": ["aws", "amazon web services", "amazon aws"],
        "category": "cloud",
        "is_technical": True,
    },
    "Azure": {
        "variants": ["azure", "microsoft azure", "ms azure"],
        "category": "cloud",
        "is_technical": True,
    },
    "GCP": {
        "variants": ["gcp", "google cloud", "google cloud platform"],
        "category": "cloud",
        "is_technical": True,
    },

    # ─── DEVOPS ────────────────────────────────────────────────────────────────
    "Docker": {
        "variants": ["docker"],
        "category": "devops",
        "is_technical": True,
    },
    "Kubernetes": {
        "variants": ["kubernetes", "k8s"],
        "category": "devops",
        "is_technical": True,
    },
    "Git": {
        "variants": ["git"],
        "category": "devops",
        "is_technical": True,
    },
    "GitHub": {
        "variants": ["github", "git hub"],
        "category": "devops",
        "is_technical": True,
    },
    "GitLab": {
        "variants": ["gitlab", "git lab"],
        "category": "devops",
        "is_technical": True,
    },
    "CI/CD": {
        "variants": ["ci/cd", "cicd", "ci cd", "continuous integration", "continuous deployment"],
        "category": "devops",
        "is_technical": True,
    },
    "Linux": {
        "variants": ["linux", "unix", "ubuntu", "centos", "debian"],
        "category": "devops",
        "is_technical": True,
    },
    "Terraform": {
        "variants": ["terraform"],
        "category": "devops",
        "is_technical": True,
    },

    # ─── DATA SCIENCE & AI ─────────────────────────────────────────────────────
    "Machine Learning": {
        "variants": ["machine learning", "ml"],
        "category": "data_science",
        "is_technical": True,
    },
    "Deep Learning": {
        "variants": ["deep learning", "dl"],
        "category": "data_science",
        "is_technical": True,
    },
    "Natural Language Processing": {
        "variants": ["natural language processing", "nlp"],
        "category": "data_science",
        "is_technical": True,
    },
    "Computer Vision": {
        "variants": ["computer vision", "cv", "image processing"],
        "category": "data_science",
        "is_technical": True,
    },
    "Data Analysis": {
        "variants": ["data analysis", "data analytics", "data analyst"],
        "category": "data_science",
        "is_technical": True,
    },
    "Data Visualization": {
        "variants": ["data visualization", "data visualisation", "dataviz"],
        "category": "data_science",
        "is_technical": True,
    },
    "Pandas": {
        "variants": ["pandas"],
        "category": "data_science",
        "is_technical": True,
    },
    "NumPy": {
        "variants": ["numpy", "num py"],
        "category": "data_science",
        "is_technical": True,
    },
    "Matplotlib": {
        "variants": ["matplotlib", "matplot"],
        "category": "data_science",
        "is_technical": True,
    },
    "Power BI": {
        "variants": ["power bi", "powerbi", "power-bi"],
        "category": "data_science",
        "is_technical": True,
    },
    "Tableau": {
        "variants": ["tableau"],
        "category": "data_science",
        "is_technical": True,
    },
    "Excel": {
        "variants": ["excel", "ms excel", "microsoft excel"],
        "category": "data_science",
        "is_technical": True,
    },

    # ─── TESTING & QA (software) ───────────────────────────────────────────────
    "Selenium": {
        "variants": ["selenium", "selenium webdriver"],
        "category": "testing",
        "is_technical": True,
    },
    "TestNG": {
        "variants": ["testng", "test ng"],
        "category": "testing",
        "is_technical": True,
    },
    "JIRA": {
        "variants": ["jira", "jira software"],
        "category": "tool",
        "is_technical": True,
    },
    "Pytest": {
        "variants": ["pytest", "py.test"],
        "category": "testing",
        "is_technical": True,
    },
    "Postman": {
        "variants": ["postman"],
        "category": "testing",
        "is_technical": True,
    },
    "REST API": {
        "variants": ["rest api", "restful api", "rest", "restful", "rest apis"],
        "category": "testing",
        "is_technical": True,
    },
    "GraphQL": {
        "variants": ["graphql", "graph ql"],
        "category": "testing",
        "is_technical": True,
    },

    # ─── QUALITY ENGINEERING (manufacturing) ───────────────────────────────────
    "ISO 9001": {
        "variants": ["iso 9001", "iso9001"],
        "category": "quality_engineering",
        "is_technical": True,
    },
    "IATF 16949": {
        "variants": ["iatf 16949", "iatf16949", "iatf"],
        "category": "quality_engineering",
        "is_technical": True,
    },
    "AS9100": {
        "variants": ["as9100", "as 9100"],
        "category": "quality_engineering",
        "is_technical": True,
    },
    "GMP": {
        "variants": ["gmp", "good manufacturing practice", "good manufacturing practices"],
        "category": "quality_engineering",
        "is_technical": True,
    },
    "HACCP": {
        "variants": ["haccp"],
        "category": "quality_engineering",
        "is_technical": True,
    },
    "Six Sigma": {
        "variants": ["six sigma", "6 sigma", "6sigma"],
        "category": "quality_engineering",
        "is_technical": True,
    },
    "Lean Manufacturing": {
        "variants": ["lean manufacturing", "lean", "lean production"],
        "category": "quality_engineering",
        "is_technical": True,
    },
    "Statistical Process Control": {
        "variants": ["statistical process control", "spc"],
        "category": "quality_engineering",
        "is_technical": True,
    },
    "Failure Mode and Effects Analysis": {
        "variants": ["failure mode and effects analysis", "fmea", "failure mode effects analysis"],
        "category": "quality_engineering",
        "is_technical": True,
    },
    "Corrective and Preventive Action": {
        "variants": ["corrective and preventive action", "capa", "corrective action preventive action"],
        "category": "quality_engineering",
        "is_technical": True,
    },
    "Root Cause Analysis": {
        "variants": ["root cause analysis", "rca"],
        "category": "quality_engineering",
        "is_technical": True,
    },
    "Value Stream Mapping": {
        "variants": ["value stream mapping", "vsm"],
        "category": "quality_engineering",
        "is_technical": True,
    },
    "APQP": {
        "variants": ["apqp", "advanced product quality planning"],
        "category": "quality_engineering",
        "is_technical": True,
    },
    "PPAP": {
        "variants": ["ppap", "production part approval process"],
        "category": "quality_engineering",
        "is_technical": True,
    },
    "Kaizen": {
        "variants": ["kaizen"],
        "category": "quality_engineering",
        "is_technical": True,
    },
    "5S": {
        "variants": ["5s"],
        "category": "quality_engineering",
        "is_technical": True,
    },
    "8D": {
        "variants": ["8d", "8d problem solving", "eight disciplines"],
        "category": "quality_engineering",
        "is_technical": True,
    },
    "DMAIC": {
        "variants": ["dmaic", "six sigma dmaic"],
        "category": "quality_engineering",
        "is_technical": True,
    },
    "Control Plans": {
        "variants": ["control plans", "control plan"],
        "category": "quality_engineering",
        "is_technical": True,
    },
    "Audit": {
        "variants": ["audit", "quality audit", "internal audit"],
        "category": "quality_engineering",
        "is_technical": True,
    },
    "FSSAI": {
        "variants": ["fssai"],
        "category": "quality_engineering",
        "is_technical": True,
    },

    # ─── SOFT SKILLS ───────────────────────────────────────────────────────────
    "Communication": {
        "variants": ["communication", "communication skills"],
        "category": "soft_skill",
        "is_technical": False,
    },
    "Leadership": {
        "variants": ["leadership", "team leadership", "people management"],
        "category": "soft_skill",
        "is_technical": False,
    },
    "Teamwork": {
        "variants": ["teamwork", "team player", "collaboration", "collaborative"],
        "category": "soft_skill",
        "is_technical": False,
    },
    "Problem Solving": {
        "variants": ["problem solving", "problem-solving"],
        "category": "soft_skill",
        "is_technical": False,
    },
    "Analytical Thinking": {
        "variants": ["analytical thinking", "analytical skills", "analytical"],
        "category": "soft_skill",
        "is_technical": False,
    },
    "Attention to Detail": {
        "variants": ["attention to detail", "detail oriented", "detail-oriented"],
        "category": "soft_skill",
        "is_technical": False,
    },
    "Time Management": {
        "variants": ["time management"],
        "category": "soft_skill",
        "is_technical": False,
    },
    "Project Management": {
        "variants": ["project management", "program management"],
        "category": "methodology",
        "is_technical": False,
    },
    "Adaptability": {
        "variants": ["adaptability", "adaptable", "flexible"],
        "category": "soft_skill",
        "is_technical": False,
    },
}


# ─── SKILL STACKS ──────────────────────────────────────────────────────────────

SKILL_STACKS: dict[str, list[str]] = {
    "mern": ["MongoDB", "Express", "React", "Node"],
    "mean": ["MongoDB", "Express", "Angular", "Node"],
    "lamp": ["Linux", "Apache", "MySQL", "PHP"],
    "django rest": ["Django", "REST API", "Python"],
    "data science": ["Python", "Pandas", "NumPy", "Machine Learning", "Data Analysis"],
    "devops": ["Docker", "Kubernetes", "CI/CD", "Git", "Linux"],
}


# ─── SKILL LEVEL INDICATORS ────────────────────────────────────────────────────

SKILL_LEVEL_INDICATORS: dict[str, list[str]] = {
    "beginner": [
        "basic", "familiar", "knowledge of", "exposure to", "learning", "beginner",
    ],
    "intermediate": [
        "working knowledge", "familiar with", "understanding of", "intermediate",
        "used", "worked with",
    ],
    "advanced": [
        "proficient", "experienced", "strong", "advanced", "expert in",
        "hands-on", "skilled",
    ],
    "expert": [
        "expert", "specialist", "deep expertise", "extensive experience",
        "mastery", "lead", "architect",
    ],
}