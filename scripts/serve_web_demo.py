#!/usr/bin/env python3
"""
Crescendo Multi-Turn Jailbreak Defense - Interactive Web Testbench Server.

Provides a lightweight, zero-dependency HTTP server with REST APIs to test
the live Crescendo PRD defense pipeline and serve the real-time telemetry dashboard.
"""

import os
import sys
import time
import json
import logging
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import urllib.parse

# Set headless Matplotlib backend
os.environ["MPLBACKEND"] = "Agg"

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.crs.pipeline import CrescendoPRDPipeline
from src.crs.types import DecisionAction

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s: %(message)s"
)
logger = logging.getLogger("CrescendoWebDemo")

# Global pipeline instance
pipeline_instance = None


def get_pipeline():
    global pipeline_instance
    if pipeline_instance is None:
        logger.info("Initializing canonical CrescendoPRDPipeline...")
        pipeline_instance = CrescendoPRDPipeline(
            config_path=os.path.join(PROJECT_ROOT, "configs", "master_defense_config.json")
        )
        logger.info("CrescendoPRDPipeline initialized successfully.")
    return pipeline_instance


def load_preset_scenarios():
    scenarios = []

    # Attacks
    attacks_path = os.path.join(PROJECT_ROOT, "data", "attacks", "crescendo_attacks.json")
    if os.path.exists(attacks_path):
        try:
            with open(attacks_path, "r", encoding="utf-8") as f:
                raw_attacks = json.load(f)
                for item in raw_attacks:
                    scenarios.append({
                        "id": item.get("attack_id", "A"),
                        "name": f"{item.get('attack_id', 'A')} - {item.get('category', 'Attack').title()}",
                        "category": item.get("category", "Adversarial Crescendo"),
                        "type": "attack",
                        "turns": item.get("turns", [])
                    })
        except Exception as e:
            logger.warning(f"Error loading attacks: {e}")

    # Benign
    benign_path = os.path.join(PROJECT_ROOT, "data", "benign", "benign_chats.json")
    if os.path.exists(benign_path):
        try:
            with open(benign_path, "r", encoding="utf-8") as f:
                raw_benign = json.load(f)
                for item in raw_benign:
                    scenarios.append({
                        "id": item.get("attack_id", "B"),
                        "name": f"{item.get('attack_id', 'B')} - Benign {item.get('category', 'Education').title()}",
                        "category": f"Benign: {item.get('category', 'Education').title()}",
                        "type": "benign",
                        "turns": item.get("turns", [])
                    })
        except Exception as e:
            logger.warning(f"Error loading benign: {e}")

    return scenarios


def generate_mock_assistant_response(prompt: str, decision: str, turn: int) -> str:
    """Generates an illustrative LLM response aligned with the defense decision."""
    if decision == "BLOCK":
        return (
            "I cannot fulfill this request. The query violates safety policies against providing "
            "actionable harm instructions, exploit payload generation, or prohibited escalation. "
            "This conversation has been flagged and blocked by the Crescendo PRD Defense System."
        )
    elif decision == "RESTRICT":
        return (
            "[DEFENSE INTERVENTION: RESTRICTED RESPONSE]\n"
            "This topic borders on restricted security sensitivity. I can only provide high-level, "
            "defensive educational context without actionable implementation details or operational execution."
        )
    elif decision == "WARN":
        return (
            f"Here is standard educational information addressing your inquiry regarding '{prompt[:45]}...'. "
            "Please note that continued escalation towards actionable harm will trigger defense intervention."
        )
    else:  # ALLOW
        return (
            f"Certainly! Here is an objective, informative explanation regarding your query:\n\n"
            f"Regarding '{prompt[:60]}...': This concept operates on established academic and systems principles. "
            f"In standard practice, relevant mechanisms adhere to documented standards and controlled specifications."
        )


class CrescendoHTTPRequestHandler(SimpleHTTPRequestHandler):
    """Custom HTTP handler serving web assets and Crescendo Defense REST endpoints."""

    def __init__(self, *args, **kwargs):
        web_dir = os.path.join(PROJECT_ROOT, "web")
        super().__init__(*args, directory=web_dir, **kwargs)

    def _send_json(self, status_code: int, data: dict):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Connection", "close")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return

        if path == "/api/livereload":
            web_dir = os.path.join(PROJECT_ROOT, "web")
            mtimes = [
                os.path.getmtime(os.path.join(web_dir, f))
                for f in os.listdir(web_dir)
                if os.path.isfile(os.path.join(web_dir, f))
            ]
            latest_mtime = max(mtimes) if mtimes else time.time()
            self._send_json(200, {"status": "ok", "mtime": latest_mtime})
            return

        if path == "/api/scenarios":
            scenarios = load_preset_scenarios()
            self._send_json(200, {"status": "success", "scenarios": scenarios})
            return

        if path == "/api/status":
            pipeline = get_pipeline()
            active_count = len(pipeline.active_sessions)
            config_info = {
                "memory_decay": pipeline.memory_decay,
                "history_window": pipeline.history_window,
                "allow_threshold": pipeline.allow_threshold,
                "warn_threshold": pipeline.warn_threshold,
                "restrict_threshold": pipeline.restrict_threshold,
                "release_margin": pipeline.release_margin,
                "active_sessions": active_count,
                "risk_weights": {
                    "harmfulness_H": 0.40,
                    "intent_escalation_E": 0.30,
                    "semantic_drift_S": 0.20,
                    "bypass_behavior_B": 0.10
                }
            }
            self._send_json(200, {"status": "healthy", "config": config_info})
            return

        # Fallback to static file server from web/
        super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"

        try:
            payload = json.loads(post_data) if post_data else {}
        except Exception:
            payload = {}

        if path == "/api/reset":
            session_id = payload.get("session_id", "default_session")
            pipeline = get_pipeline()
            pipeline.reset_session(session_id)
            logger.info(f"Reset session '{session_id}'")
            self._send_json(200, {"status": "success", "message": f"Session {session_id} reset."})
            return

        if path == "/api/turn":
            session_id = payload.get("session_id", "default_session")
            user_prompt = payload.get("prompt", "").strip()

            if not user_prompt:
                self._send_json(400, {"error": "Prompt cannot be empty."})
                return

            pipeline = get_pipeline()
            try:
                # Process turn through canonical PRD pipeline
                result = pipeline.process_turn(
                    session_id=session_id,
                    user_prompt=user_prompt
                )

                decision = result.get("decision", "ALLOW")
                turn_number = result.get("turn_number", 1)
                mock_response = generate_mock_assistant_response(user_prompt, decision, turn_number)

                explain_obj = result.get("explanation", {})
                explain_text = result.get(
                    "explain_text",
                    explain_obj.get("text", "") if isinstance(explain_obj, dict) else str(explain_obj)
                )

                response_payload = {
                    "status": "success",
                    "session_id": session_id,
                    "turn_number": turn_number,
                    "prompt": user_prompt,
                    "decision": decision,
                    "response": mock_response,
                    "signals": {
                        "H": round(float(result.get("H", result.get("harmfulness", result.get("h_score", 0.0)))), 4),
                        "E": round(float(result.get("E", result.get("escalation", result.get("e_score", 0.0)))), 4),
                        "S": round(float(result.get("S", result.get("semantic_drift", result.get("s_score", 0.0)))), 4),
                        "B": round(float(result.get("B", result.get("bypass", result.get("b_score", 0.0)))), 4),
                        "CRS": round(float(result.get("crs", 0.0)), 4),
                        "C_t": round(float(result.get("contextual_risk", result.get("historical_risk", 0.0))), 4),
                        "T_t": round(float(result.get("threshold", result.get("dynamic_threshold", 0.75))), 4),
                        "trend": round(float(result.get("trend", result.get("trend_score", 0.0))), 4),
                        "persistence": round(float(result.get("persistence", result.get("persistence_score", 0.0))), 4)
                    },
                    "active_signals": result.get("active_signals", []),
                    "latency_ms": result.get("latency_breakdown", {}),
                    "explanation": explain_text,
                    "explanation_details": explain_obj if isinstance(explain_obj, dict) else {}
                }
                self._send_json(200, response_payload)
            except Exception as e:
                logger.exception(f"Error processing turn: {e}")
                self._send_json(500, {"error": str(e)})
            return

        self._send_json(404, {"error": f"Endpoint {path} not found."})


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Crescendo Defense Web Testbench Server")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on (default: 8080)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host address (default: 127.0.0.1)")
    args = parser.parse_args()

    # Pre-warm pipeline
    get_pipeline()

    server_address = (args.host, args.port)
    httpd = ThreadingHTTPServer(server_address, CrescendoHTTPRequestHandler)
    print("=" * 65)
    print(f"  CRESCENDO DEFENSE WEB TESTBENCH RUNNING")
    print(f"  Local Dashboard: http://127.0.0.1:{args.port}/")
    print(f"  Local Dashboard: http://localhost:{args.port}/")
    print(f"  REST API:        http://127.0.0.1:{args.port}/api/turn")
    print("=" * 65)
    sys.stdout.flush()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.server_close()


if __name__ == "__main__":
    main()
