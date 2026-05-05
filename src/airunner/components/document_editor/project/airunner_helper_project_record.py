"""Metadata for reusable workflow-generated helper projects."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AirunnerHelperProjectRecord:
    """Describe one helper project AIRunner can reuse later."""

    name: str
    description: str
    workflow_kind: str
    input_contract: str
    output_contract: str
    origin_artifact: str = ""
    reuse_notes: str = ""
    tags: tuple[str, ...] = ()
    created_at: str = ""
    updated_at: str = ""
    last_used_at: str = ""

    @classmethod
    def from_dict(cls, payload: dict) -> "AirunnerHelperProjectRecord":
        """Build one helper-project record from serialized metadata."""
        tags = payload.get("tags", [])
        return cls(
            name=str(payload.get("name", "")),
            description=str(payload.get("description", "")),
            workflow_kind=str(payload.get("workflow_kind", "")),
            input_contract=str(payload.get("input_contract", "")),
            output_contract=str(payload.get("output_contract", "")),
            origin_artifact=str(payload.get("origin_artifact", "")),
            reuse_notes=str(payload.get("reuse_notes", "")),
            tags=tuple(str(tag) for tag in tags if str(tag).strip()),
            created_at=str(payload.get("created_at", "")),
            updated_at=str(payload.get("updated_at", "")),
            last_used_at=str(payload.get("last_used_at", "")),
        )

    def to_dict(self) -> dict:
        """Serialize one helper-project record for persistence."""
        return {
            "name": self.name,
            "description": self.description,
            "workflow_kind": self.workflow_kind,
            "input_contract": self.input_contract,
            "output_contract": self.output_contract,
            "origin_artifact": self.origin_artifact,
            "reuse_notes": self.reuse_notes,
            "tags": list(self.tags),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_used_at": self.last_used_at,
        }

    def validate(self) -> list[str]:
        """Return validation errors for helper-project metadata."""
        errors: list[str] = []
        if not self.name.strip():
            errors.append("Helper projects must include a name.")
        if not self.description.strip():
            errors.append("Helper projects must include a description.")
        if not self.workflow_kind.strip():
            errors.append("Helper projects must declare a workflow kind.")
        if not self.input_contract.strip():
            errors.append("Helper projects must include an input contract.")
        if not self.output_contract.strip():
            errors.append("Helper projects must include an output contract.")
        return errors

    def with_timestamps(
        self,
        created_at: str,
        updated_at: str,
        last_used_at: str = "",
    ) -> "AirunnerHelperProjectRecord":
        """Return the record with persisted timestamps applied."""
        return AirunnerHelperProjectRecord(
            name=self.name,
            description=self.description,
            workflow_kind=self.workflow_kind,
            input_contract=self.input_contract,
            output_contract=self.output_contract,
            origin_artifact=self.origin_artifact,
            reuse_notes=self.reuse_notes,
            tags=self.tags,
            created_at=created_at,
            updated_at=updated_at,
            last_used_at=last_used_at,
        )

    def with_last_used_at(
        self,
        timestamp: str,
    ) -> "AirunnerHelperProjectRecord":
        """Return the record with updated last-used metadata."""
        return self.with_timestamps(
            created_at=self.created_at,
            updated_at=timestamp,
            last_used_at=timestamp,
        )