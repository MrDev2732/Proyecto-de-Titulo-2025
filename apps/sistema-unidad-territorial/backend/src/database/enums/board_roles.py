from enum import Enum


class BoardRole(Enum):
    """Board member roles in community governance."""

    PRESIDENT = "president"
    SECRETARY = "secretary" 
    TREASURER = "treasurer"
    VOCAL = "vocal"  # Board member without specific role

    def __str__(self) -> str:
        return self.value

    @property
    def display_name(self) -> str:
        """Human-readable display name."""
        names = {
            self.PRESIDENT: "Presidente",
            self.SECRETARY: "Secretario",
            self.TREASURER: "Tesorero", 
            self.VOCAL: "Vocal"
        }
        return names[self]

    @property
    def is_executive(self) -> bool:
        """Check if this is an executive role (president, secretary, treasurer)."""
        return self in (self.PRESIDENT, self.SECRETARY, self.TREASURER)
