from typing import Dict, Any, Optional
from app.models import Ruleset
from app.database import get_db
from sqlalchemy.orm import Session

class RuleManager:
    def __init__(self, db: Optional[Session] = None):
        if db is None:
            self.db = next(get_db())
        else:
            self.db = db

    def load_rules(self, restaurant_id: str) -> Dict[str, Any]:
        ruleset = self.db.query(Ruleset).filter_by(restaurant_id=restaurant_id).first()
        if ruleset and ruleset.rules_json:
            return ruleset.rules_json
        return {}

    def save_rules(self, restaurant_id: str, rules: Dict[str, Any]) -> None:
        ruleset = self.db.query(Ruleset).filter_by(restaurant_id=restaurant_id).first()
        if not ruleset:
            ruleset = Ruleset(restaurant_id=restaurant_id, rules_json=rules)
            self.db.add(ruleset)
        else:
            ruleset.rules_json = rules
        self.db.commit()

    def update_rules(self, restaurant_id: str, new_rules: Dict[str, Any]) -> None:
        ruleset = self.db.query(Ruleset).filter_by(restaurant_id=restaurant_id).first()
        if not ruleset:
            ruleset = Ruleset(restaurant_id=restaurant_id, rules_json=new_rules)
            self.db.add(ruleset)
        else:
            if ruleset.rules_json:
                ruleset.rules_json.update(new_rules)
            else:
                ruleset.rules_json = new_rules
        self.db.commit()

    def clear_rules(self, restaurant_id: str) -> bool:
        """Clear all rules for a restaurant. Returns True if rules were cleared, False if no rules existed."""
        ruleset = self.db.query(Ruleset).filter_by(restaurant_id=restaurant_id).first()
        if ruleset:
            self.db.delete(ruleset)
            self.db.commit()
            return True
        return False
