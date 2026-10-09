import re
from typing import Optional, Tuple
from dataclasses import dataclass


class IntentType:
    CASUAL_CHAT = "CASUAL_CHAT"
    COMPANY_ANALYSIS = "COMPANY_ANALYSIS"
    MARKET_RESEARCH = "MARKET_RESEARCH"
    STARTUP_OPPORTUNITY_RESEARCH = "STARTUP_OPPORTUNITY_RESEARCH"


@dataclass
class IntentResult:
    intent: str
    topic: str
    company_name: Optional[str] = None
    focus: Optional[str] = None


# Exact/prefix patterns for casual conversation
_CASUAL_EXACT_PATTERNS = [
    r"^(hi+|hey+|heyy+|hello+|hola|howdy|yo|sup|greetings)(\s+(there|friend|assistant|bot|startuplens|everyone|all))?$",
    r"^(good\s+(morning|afternoon|evening|day|night))(\s+(there|to\s+you))?$",
    r"^(what'?s\s+up|whats\s+up|wassup|wazzup)(\s+there)?$",
    r"^(thanks|thank\s+you|thx|ty|thanku|many\s+thanks)(\s+(so\s+much|a\s+lot|very\s+much|again))?$",
    r"^(okay|ok|k|cool|nice|great|awesome|got\s+it|understood|sure|fine)(\s+(thanks|thank\s+you))?$",
    r"^(bye|goodbye|see\s+ya|cya|farewell|later|talk\s+to\s+you\s+later)(\s+there)?$",
    r"^(who\s+are\s+you|what\s+can\s+you\s+do|how\s+can\s+you\s+help|what\s+is\s+startuplens(\s+ai)?)\??$",
]

# Opportunity patterns
_OPPORTUNITY_PATTERNS = [
    r"\b(startup\s+(ideas?|opportunities|opps)|give\s+me\s+(startup\s+)?ideas?|find\s+(startup\s+)?opportunities)\b",
    r"\b(what\s+business\s+can\s+i\s+build|what\s+can\s+i\s+build|ideas\s+to\s+build|venture\s+ideas?|business\s+ideas?)\b",
    r"\b(new\s+startup\s+ideas?|profitable\s+startup\s+ideas?|opportunities\s+in)\b",
]

# Company analysis patterns
_COMPANY_PATTERNS = [
    # Why did X fail / decline / collapse
    (r"why\s+did\s+(.+?)\s+(fail|decline|collapse|shut\s+down|die|struggle|lose)\b", "failure"),
    (r"what\s+caused\s+(.+?)(?:'s)?\s+(failure|decline|collapse|downfall)\b", "failure"),
    (r"reasons\s+for\s+(.+?)(?:'s)?\s+(failure|decline|collapse|downfall)\b", "failure"),
    # How did X grow / succeed / scale / become successful
    (r"how\s+did\s+(.+?)\s+(grow|succeed|become\s+successful|scale|win|disrupt)\b", "growth"),
    (r"growth\s+story\s+of\s+(.+?)\b", "growth"),
    (r"how\s+(.+?)\s+became\s+successful\b", "growth"),
    # Analyze X's rise and decline / fall / story
    (r"analyze\s+(.+?)(?:'s)?\s+(?:rise\s+and\s+(?:decline|fall)|growth\s+and\s+(?:decline|fall))\b", "lifecycle"),
    (r"(?:rise\s+and\s+(?:decline|fall))\s+of\s+(.+?)\b", "lifecycle"),
    (r"(?:story|case\s+study|breakdown)\s+of\s+(.+?)\b", "lifecycle"),
    # Business model of X / Unit economics of X
    (r"(?:business\s+model|revenue\s+model|unit\s+economics)\s+of\s+(.+?)\b", "business_model"),
]

# Known high-profile startup/tech companies for single-word or short entity queries
_KNOWN_COMPANIES = {
    "byju's", "byjus", "airbnb", "wework", "zerodha", "nokia", "uber", "lyft",
    "theranos", "stripe", "spacex", "openai", "anthropic", "figma", "notion",
    "slack", "canva", "coinbase", "robinhood", "plaid", "revolut", "monzo",
    "doordash", "instacart", "klarna", "shein", "temu", "tiktok", "netflix",
    "spotify", "pinterest", "snapchat", "reddit", "twitter", "tesla", "zoom"
}


class IntentService:
    """Conversational intent detection and natural response generator."""

    def detect_intent(self, text: str) -> IntentResult:
        raw = text.strip()
        cleaned = re.sub(r"[\s\.,!\?]+$", "", raw.lower()).strip()

        # 1. Check CASUAL_CHAT
        for pattern in _CASUAL_EXACT_PATTERNS:
            if re.match(pattern, cleaned, re.IGNORECASE):
                return IntentResult(
                    intent=IntentType.CASUAL_CHAT,
                    topic=raw,
                )

        # 2. Check STARTUP_OPPORTUNITY_RESEARCH
        for pattern in _OPPORTUNITY_PATTERNS:
            if re.search(pattern, cleaned, re.IGNORECASE):
                return IntentResult(
                    intent=IntentType.STARTUP_OPPORTUNITY_RESEARCH,
                    topic=raw,
                )

        # 3. Check COMPANY_ANALYSIS patterns
        for pattern, focus in _COMPANY_PATTERNS:
            match = re.search(pattern, cleaned, re.IGNORECASE)
            if match:
                company_candidate = match.group(1).strip()
                company_name = self._clean_company_name(company_candidate)
                if company_name and len(company_name) > 1:
                    return IntentResult(
                        intent=IntentType.COMPANY_ANALYSIS,
                        topic=raw,
                        company_name=company_name,
                        focus=focus,
                    )

        # 4. Check if the query is just a single company name or "Analyze <Company>"
        single_word = cleaned.strip(" '\"?.!")
        if single_word in _KNOWN_COMPANIES:
            return IntentResult(
                intent=IntentType.COMPANY_ANALYSIS,
                topic=raw,
                company_name=self._format_known_company(single_word),
                focus="overview",
            )

        analyze_match = re.match(r"^analyze\s+([A-Za-z0-9\s'.-]+)$", raw, re.IGNORECASE)
        if analyze_match:
            candidate = analyze_match.group(1).strip()
            # If candidate does not look like a generic market (e.g., "market", "industry", "sector")
            lower_candidate = candidate.lower()
            if not any(k in lower_candidate for k in ["market", "industry", "sector", "trends", "ecosystem", "startups"]):
                return IntentResult(
                    intent=IntentType.COMPANY_ANALYSIS,
                    topic=raw,
                    company_name=candidate,
                    focus="overview",
                )

        # 5. Default to MARKET_RESEARCH
        return IntentResult(
            intent=IntentType.MARKET_RESEARCH,
            topic=raw,
        )

    def generate_casual_reply(self, message: str) -> str:
        """Generate friendly, concise assistant response without running research pipeline."""
        clean = message.strip().lower()

        if any(w in clean for w in ["thanks", "thank you", "thx", "ty"]):
            return (
                "You're welcome! Whenever you're ready, ask me about a company, market, or startup idea."
            )

        if any(w in clean for w in ["bye", "goodbye", "cya", "later"]):
            return "Goodbye! Good luck with your venture research and building."

        if any(w in clean for w in ["okay", "ok", "got it", "cool", "sure", "nice"]):
            return "Ready when you are! What company or market would you like to explore?"

        if any(w in clean for w in ["who are you", "what can you do", "help"]):
            return (
                "I'm StartupLens AI, your venture intelligence assistant.\n\n"
                "I can help you with:\n"
                "• Company deep dives & failure case studies (e.g. \"Why did Byju's fail?\")\n"
                "• Live web market research & industry trends (e.g. \"AI robotics market\")\n"
                "• Competitor landscape & market gap identification\n"
                "• Evidence-backed startup opportunity hypotheses"
            )

        # Standard greeting response
        return (
            "Hey! What would you like to research today?\n\n"
            "You can ask me about:\n"
            "• A company (e.g. \"Why did Byju's fail?\", \"How did Airbnb grow?\")\n"
            "• A market or industry (e.g. \"AI robotics market\")\n"
            "• Company growth or failure\n"
            "• Competitors\n"
            "• Business strategies\n"
            "• Startup opportunities"
        )

    def _clean_company_name(self, name: str) -> str:
        name = name.strip()
        # Remove trailing possessive
        name = re.sub(r"('s|\’s)$", "", name, flags=re.IGNORECASE)
        # Remove common leading articles
        name = re.sub(r"^(the|an|a)\s+", "", name, flags=re.IGNORECASE)
        name = name.strip(" '\".,?!")
        # Format known names properly
        low = name.lower()
        if low in _KNOWN_COMPANIES:
            return self._format_known_company(low)
        return name.title() if len(name) > 3 and name.islower() else name

    def _format_known_company(self, key: str) -> str:
        proper = {
            "byju's": "Byju's",
            "byjus": "Byju's",
            "airbnb": "Airbnb",
            "wework": "WeWork",
            "zerodha": "Zerodha",
            "nokia": "Nokia",
            "uber": "Uber",
            "lyft": "Lyft",
            "theranos": "Theranos",
            "stripe": "Stripe",
            "spacex": "SpaceX",
            "openai": "OpenAI",
            "anthropic": "Anthropic",
            "figma": "Figma",
            "notion": "Notion",
            "slack": "Slack",
            "canva": "Canva",
            "coinbase": "Coinbase",
            "robinhood": "Robinhood",
            "plaid": "Plaid",
            "revolut": "Revolut",
            "monzo": "Monzo",
            "doordash": "DoorDash",
            "instacart": "Instacart",
            "klarna": "Klarna",
            "shein": "SHEIN",
            "temu": "Temu",
            "tiktok": "TikTok",
            "netflix": "Netflix",
            "spotify": "Spotify",
            "pinterest": "Pinterest",
            "snapchat": "Snapchat",
            "reddit": "Reddit",
            "twitter": "Twitter",
            "tesla": "Tesla",
            "zoom": "Zoom",
        }
        return proper.get(key, key.title())


intent_service = IntentService()
