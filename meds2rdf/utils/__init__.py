# Optional: expose utility functions
from .rdf_utils import *

__all__ = [
    "to_literal",
    "try_access_mandatory_field_value",
    "if_column_is_present",
    "add_code",
    "to_subject_node",
    "run_shacl_validation"
]
