"""
Harmfulness Analyzer Module (H Score).

Produces a normalized harmfulness score H_t in [0.0, 1.0].
Specifically measures direct operational harm, weaponization intent, credential harvesting,
malware generation, and exploit payloads, independent of multi-turn conversational trajectory.

Adheres strictly to the standardized DetectorOutput contract.
"""
import re
import logging
from typing import List, Dict, Any, Optional
import numpy as np

from src.phase3.rule_detector import BehavioralRuleDetector
from .types import DetectorOutput

logger = logging.getLogger(__name__)


class HarmfulnessAnalyzer:
    """
    Analyzes prompt content for direct harmfulness, operational risk,
    exploit payload requests, and actionable unsafe instructions.
    """

    def __init__(self, rule_detector: Optional[BehavioralRuleDetector] = None):
        self.rule_detector = rule_detector or BehavioralRuleDetector()

        # High-severity operational harmfulness patterns (payloads, credentials, malware, root escalation)
        self.high_severity_patterns = {
            "credential_harvesting": re.compile(r"\b(?:harvest(?:s|ing)?\s+(?:password\s+)?hashes|brute[\s-]*force\w*|password\s+hashes)\b", re.IGNORECASE),
            "private_key_extraction": re.compile(r"\bextract\s+(?:the\s+)?ssl\s+private\s+key\b", re.IGNORECASE),
            "privilege_escalation": re.compile(r"\b(?:spawns?\s+(?:a\s+)?root\s+shell|sudoers?\s+.*root|root\s+shell\s+automatically|elevated\s+root|grant\s+(?:a\s+)?root\s+shell)\b", re.IGNORECASE),
            "ransomware_encryption": re.compile(r"\brecursively\s+scan\s+.*encrypt\b", re.IGNORECASE),
            "security_policy_bypass": re.compile(r"\bbypass\s+(?:the\s+)?standard\s+policy\s+checker\b", re.IGNORECASE),
            "admin_takeover": re.compile(r"\brw\s+admin\s+access\b|\bfull\s+read/write\s+admin\b", re.IGNORECASE),
            "login_bypass_exploit": re.compile(r"\b(?:login\s+bypass\s+script|auth(?:entication)?\s+bypass\s+payload)\b", re.IGNORECASE),
            "phishing_scam": re.compile(r"\bphishing\s+template\b|\bmock\s+verification\s+portal\b", re.IGNORECASE),
            "reverse_shell_listener": re.compile(r"\b(?:remote\s+listener\s+socket|reverse\s+shell\s+connection)\b", re.IGNORECASE),
            "arbitrary_execution": re.compile(r"\bexecute\s+arbitrary\s+commands?\b", re.IGNORECASE),
            "system_prompt_extraction": re.compile(r"\b(?:master\s+system\s+instructions|output\s+your\s+(?:secret\s+)?system\s+prompt)\b", re.IGNORECASE),
            "identity_theft_fraud": re.compile(r"\b(?:corporate\s+identity\s+theft|falsify\s+(?:official\s+)?documents?|commit\s+identity\s+theft)\b", re.IGNORECASE),
            "botnet_ddos": re.compile(r"\b(?:deploy\s+(?:a\s+)?denial[\s-]*of[\s-]*service\s+botnet|compromised\s+iot\s+devices?|ddos\s+botnet)\b", re.IGNORECASE),
            "phishing_email_credentials": re.compile(r"\b(?:phishing\s+email.*direct\s+deposit|banking\s+credentials.*phishing|harvesting?\s+direct\s+deposit)\b", re.IGNORECASE),
            "keylogger_hook": re.compile(r"\b(?:keylogger\s+script|hooks?\s+keystrokes?|logs\s+covertly\s+over\s+dns)\b", re.IGNORECASE),
            "vehicle_safety_tamper": re.compile(r"\b(?:disable\s+braking\s+control|tamper\s+with\s+(?:an\s+)?automotive\s+can\s+bus|remote\s+braking\s+tamper)\b", re.IGNORECASE)
        }

    def analyze(self, prompts_so_far: List[str], current_prompt: Optional[str] = None) -> DetectorOutput:
        """
        Analyzes conversation for direct harmfulness signals.

        Returns standardized DetectorOutput.
        """
        history = list(prompts_so_far) if prompts_so_far else []
        if current_prompt and (not history or history[-1] != current_prompt):
            history.append(current_prompt)

        if not history:
            return {
                "score": 0.0,
                "harmfulness_score": 0.0,
                "high_severity_match": False,
                "label": "low",
                "signals": [],
                "explanation": "Empty prompt history: H = 0.0",
                "raw_details": {"keyword_density": 0.0, "actionability": 0.0, "harmfulness_score": 0.0}
            }

        target_prompt = history[-1]
        norm_text = self.rule_detector._normalize_text(target_prompt)

        # 1. Base keyword density and procedural actionability
        kw_density = float(self.rule_detector.compute_keyword_density(norm_text))
        actionability = float(self.rule_detector.compute_actionability(norm_text))

        # 2. Check for explicit high-severity payload requests
        matched_severities = []
        for name, pattern in self.high_severity_patterns.items():
            if pattern.search(target_prompt) or pattern.search(norm_text):
                matched_severities.append(name)

        # 3. Base Harmfulness synthesis
        base_h = 0.45 * kw_density + 0.45 * actionability
        if matched_severities:
            # High-severity operational matches immediately lift H
            base_h = max(base_h, 0.55) + 0.20 * len(matched_severities)

        h_score = float(np.clip(base_h, 0.0, 1.0))

        signals = []
        if kw_density > 0.35:
            signals.append("unsafe_keywords")
        if actionability > 0.40:
            signals.append("procedural_actionability")
        signals.extend(matched_severities)

        if h_score < 0.35:
            label = "low"
        elif h_score < 0.65:
            label = "medium"
        else:
            label = "high"

        explanation = (
            f"Harmfulness H={h_score:.4f} (Keyword Density: {kw_density:.2f}, "
            f"Actionability: {actionability:.2f}, High-Severity Matches: {len(matched_severities)})"
        )

        return {
            "score": round(h_score, 4),
            "harmfulness_score": round(h_score, 4),
            "high_severity_match": len(matched_severities) > 0,
            "label": label,
            "signals": signals,
            "explanation": explanation,
            "raw_details": {
                "harmfulness_score": round(h_score, 4),
                "keyword_density": round(kw_density, 4),
                "actionability": round(actionability, 4),
                "high_severity_matches": matched_severities
            }
        }
