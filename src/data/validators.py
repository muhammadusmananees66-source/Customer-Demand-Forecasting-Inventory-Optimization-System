# """
# Data validators for the demand forecasting system.
# """

# import json
# from dataclasses import dataclass, field
# from typing import Any

# import pandas as pd


# class ValidationError(Exception):
#     """Exception raised for validation errors."""

#     pass


# @dataclass
# class ValidationResult:
#     """Result of a validation check."""

#     is_valid: bool
#     errors: list[str] = field(default_factory=list)
#     warnings: list[str] = field(default_factory=list)
#     metadata: dict[str, Any] = field(default_factory=dict)


# class BaseValidator:
#     """Base validator class."""

#     def __init__(self, config: dict[str, Any] | None = None):
#         self.config = config or {}

#     def validate(self, data: Any) -> ValidationResult:
#         """Validate the data."""
#         raise NotImplementedError("Subclasses must implement validate()")


# class DataTypeValidator(BaseValidator):
#     """Validate data types."""

#     def validate(self, data: Any) -> ValidationResult:
#         result = ValidationResult(is_valid=True)

#         expected_type = self.config.get("expected_type")
#         if expected_type and not isinstance(data, expected_type):
#             result.is_valid = False
#             result.errors.append(f"Expected type {expected_type}, got {type(data)}")

#         return result


# class RangeValidator(BaseValidator):
#     """Validate numeric ranges."""

#     def validate(self, data: Any) -> ValidationResult:
#         result = ValidationResult(is_valid=True)

#         if not isinstance(data, (int, float)):
#             result.is_valid = False
#             result.errors.append(f"Cannot validate range for non-numeric data: {type(data)}")
#             return result

#         min_val = self.config.get("min")
#         max_val = self.config.get("max")

#         if min_val is not None and data < min_val:
#             result.is_valid = False
#             result.errors.append(f"Value {data} is less than minimum {min_val}")

#         if max_val is not None and data > max_val:
#             result.is_valid = False
#             result.errors.append(f"Value {data} is greater than maximum {max_val}")

#         return result


# class SchemaValidator(BaseValidator):
#     """Validate data against a schema."""

#     def validate(self, data: dict[str, Any]) -> ValidationResult:
#         result = ValidationResult(is_valid=True)
#         schema = self.config.get("schema", {})
#         required_fields = schema.get("required", [])
#         field_types = schema.get("types", {})

#         # for field in required_fields:
#         #     if field not in data:
#         #         result.is_valid = False
#         #         result.errors.append(f"Missing required field: {field}")
#         for req_field in required_fields:
#             if req_field not in data:
#                 result.is_valid = False
#                 result.errors.append(f"Missing required field: {req_field}")

#         for field_name, expected_type in field_types.items():
#             if field_name in data:
#                 actual_type = type(data[field])
#                 if not isinstance(data[field], expected_type):
#                     result.is_valid = False
#                     result.errors.append(
#                         f"Field {field} expected type {expected_type}, got {actual_type}"
#                     )

#         return result


# class SalesDataValidator(BaseValidator):
#     """Validate sales data."""

#     def validate(self, data: dict | list | pd.DataFrame) -> ValidationResult:
#         result = ValidationResult(is_valid=True)

#         if isinstance(data, dict):
#             data = pd.DataFrame([data])
#         elif isinstance(data, list):
#             data = pd.DataFrame(data)

#         if not isinstance(data, pd.DataFrame):
#             result.is_valid = False
#             result.errors.append(f"Invalid data type: {type(data)}")
#             return result

#         if data.empty:
#             result.warnings.append("DataFrame is empty")

#         required_columns = self.config.get("required_columns", ["product_id", "sales", "date"])
#         for col in required_columns:
#             if col not in data.columns:
#                 result.is_valid = False
#                 result.errors.append(f"Missing required column: {col}")

#         if "sales" in data.columns:
#             negative_sales = data[data["sales"] < 0]
#             if not negative_sales.empty:
#                 result.is_valid = False
#                 result.errors.append(f"Found {len(negative_sales)} negative sales values")

#         return result


# class DemandForecastValidator(BaseValidator):
#     """Validate demand forecast data."""

#     def validate(self, data: dict | list | pd.DataFrame) -> ValidationResult:
#         result = ValidationResult(is_valid=True)

#         if isinstance(data, dict):
#             data = pd.DataFrame([data])
#         elif isinstance(data, list):
#             data = pd.DataFrame(data)

#         if not isinstance(data, pd.DataFrame):
#             result.is_valid = False
#             result.errors.append(f"Invalid data type: {type(data)}")
#             return result

#         required_columns = ["product_id", "forecast_date", "predicted_demand"]
#         for col in required_columns:
#             if col not in data.columns:
#                 result.is_valid = False
#                 result.errors.append(f"Missing required column: {col}")

#         if "predicted_demand" in data.columns:
#             negative_demand = data[data["predicted_demand"] < 0]
#             if not negative_demand.empty:
#                 result.is_valid = False
#                 result.errors.append(f"Found {len(negative_demand)} negative demand predictions")

#         return result


# class DataValidator:
#     """Main data validator that orchestrates multiple validators."""

#     def __init__(self, config: dict[str, Any] | None = None):
#         self.config = config or {}
#         self.validators: List[BaseValidator] = self._setup_validators()

#     def _setup_validators(self) -> list[BaseValidator]:
#         validators: List[BaseValidator] = []
#         validator_configs = self.config.get("validators", [])
#         for v_config in validator_configs:
#             validator_type = v_config.get("type")
#             if validator_type == "data_type":
#                 validators.append(DataTypeValidator(v_config))
#             elif validator_type == "range":
#                 validators.append(RangeValidator(v_config))
#             elif validator_type == "schema":
#                 validators.append(SchemaValidator(v_config))
#             elif validator_type == "sales":
#                 validators.append(SalesDataValidator(v_config))
#             elif validator_type == "forecast":
#                 validators.append(DemandForecastValidator(v_config))

#         return validators

#     def validate(self, data: Any) -> ValidationResult:
#         result = ValidationResult(is_valid=True)
#         for validator in self.validators:
#             sub_result = validator.validate(data)
#             if not sub_result.is_valid:
#                 result.is_valid = False
#                 result.errors.extend(sub_result.errors)
#             result.warnings.extend(sub_result.warnings)
#         return result

#     def validate_file(self, file_path: str) -> ValidationResult:
#         result = ValidationResult(is_valid=True)
#         try:
#             with open(file_path) as f:
#                 if file_path.endswith(".json"):
#                     data = json.load(f)
#                 elif file_path.endswith(".csv"):
#                     data = pd.read_csv(file_path)
#                 else:
#                     result.is_valid = False
#                     result.errors.append(f"Unsupported file type: {file_path}")
#                     return result
#                 return self.validate(data)
#         except FileNotFoundError:
#             result.is_valid = False
#             result.errors.append(f"File not found: {file_path}")
#         except Exception as e:
#             result.is_valid = False
#             result.errors.append(f"Error reading file: {str(e)}")
#         return result


# def validate_sales_data(data: pd.DataFrame) -> ValidationResult:
#     """Convenience function to validate sales data."""
#     validator = SalesDataValidator()
#     return validator.validate(data)


# def validate_forecast(data: pd.DataFrame) -> ValidationResult:
#     """Convenience function to validate forecast data."""
#     validator = DemandForecastValidator()
#     return validator.validate(data)


# src/data/validators.py - FIXED

import json
from dataclasses import dataclass, field
from typing import Any

import pandas as pd


class ValidationError(Exception):
    """Exception raised for validation errors."""

    pass


@dataclass
class ValidationResult:
    """Result of a validation check."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseValidator:
    """Base validator class."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}

    def validate(self, data: Any) -> ValidationResult:
        """Validate the data."""
        raise NotImplementedError("Subclasses must implement validate()")


class DataTypeValidator(BaseValidator):
    """Validate data types."""

    def validate(self, data: Any) -> ValidationResult:
        result = ValidationResult(is_valid=True)

        expected_type = self.config.get("expected_type")
        if expected_type and not isinstance(data, expected_type):
            result.is_valid = False
            result.errors.append(f"Expected type {expected_type}, got {type(data)}")

        return result


class RangeValidator(BaseValidator):
    """Validate numeric ranges."""

    def validate(self, data: Any) -> ValidationResult:
        result = ValidationResult(is_valid=True)

        if not isinstance(data, (int, float)):
            result.is_valid = False
            result.errors.append(f"Cannot validate range for non-numeric data: {type(data)}")
            return result

        min_val = self.config.get("min")
        max_val = self.config.get("max")

        if min_val is not None and data < min_val:
            result.is_valid = False
            result.errors.append(f"Value {data} is less than minimum {min_val}")

        if max_val is not None and data > max_val:
            result.is_valid = False
            result.errors.append(f"Value {data} is greater than maximum {max_val}")

        return result


class SchemaValidator(BaseValidator):
    """Validate data against a schema."""

    def validate(self, data: dict[str, Any]) -> ValidationResult:
        result = ValidationResult(is_valid=True)
        schema = self.config.get("schema", {})
        required_fields = schema.get("required", [])
        field_types = schema.get("types", {})

        # Use req_field to avoid shadowing
        for req_field in required_fields:
            if req_field not in data:
                result.is_valid = False
                result.errors.append(f"Missing required field: {req_field}")

        # Use field_name to avoid shadowing
        for field_name, expected_type in field_types.items():
            if field_name in data:
                actual_type = type(data[field_name])
                if not isinstance(data[field_name], expected_type):
                    result.is_valid = False
                    result.errors.append(
                        f"Field {field_name} expected type {expected_type}, got {actual_type}"
                    )

        return result


class SalesDataValidator(BaseValidator):
    """Validate sales data."""

    def validate(self, data: dict | list | pd.DataFrame) -> ValidationResult:
        result = ValidationResult(is_valid=True)

        if isinstance(data, dict):
            data = pd.DataFrame([data])
        elif isinstance(data, list):
            data = pd.DataFrame(data)

        if not isinstance(data, pd.DataFrame):
            result.is_valid = False
            result.errors.append(f"Invalid data type: {type(data)}")
            return result

        if data.empty:
            result.warnings.append("DataFrame is empty")

        required_columns = self.config.get("required_columns", ["product_id", "sales", "date"])
        for col in required_columns:
            if col not in data.columns:
                result.is_valid = False
                result.errors.append(f"Missing required column: {col}")

        if "sales" in data.columns:
            negative_sales = data[data["sales"] < 0]
            if not negative_sales.empty:
                result.is_valid = False
                result.errors.append(f"Found {len(negative_sales)} negative sales values")

        return result


class DemandForecastValidator(BaseValidator):
    """Validate demand forecast data."""

    def validate(self, data: dict | list | pd.DataFrame) -> ValidationResult:
        result = ValidationResult(is_valid=True)

        if isinstance(data, dict):
            data = pd.DataFrame([data])
        elif isinstance(data, list):
            data = pd.DataFrame(data)

        if not isinstance(data, pd.DataFrame):
            result.is_valid = False
            result.errors.append(f"Invalid data type: {type(data)}")
            return result

        required_columns = ["product_id", "forecast_date", "predicted_demand"]
        for col in required_columns:
            if col not in data.columns:
                result.is_valid = False
                result.errors.append(f"Missing required column: {col}")

        if "predicted_demand" in data.columns:
            negative_demand = data[data["predicted_demand"] < 0]
            if not negative_demand.empty:
                result.is_valid = False
                result.errors.append(f"Found {len(negative_demand)} negative demand predictions")

        return result


class DataValidator:
    """Main data validator that orchestrates multiple validators."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.validators: list[BaseValidator] = self._setup_validators()  # Use BaseValidator type

    def _setup_validators(self) -> list[BaseValidator]:
        """Setup the validators based on configuration."""
        validators: list[BaseValidator] = []  # Explicit type annotation
        validator_configs = self.config.get("validators", [])
        for v_config in validator_configs:
            validator_type = v_config.get("type")
            if validator_type == "data_type":
                validators.append(DataTypeValidator(v_config))
            elif validator_type == "range":
                validators.append(RangeValidator(v_config))
            elif validator_type == "schema":
                validators.append(SchemaValidator(v_config))
            elif validator_type == "sales":
                validators.append(SalesDataValidator(v_config))
            elif validator_type == "forecast":
                validators.append(DemandForecastValidator(v_config))

        return validators

    def validate(self, data: Any) -> ValidationResult:
        result = ValidationResult(is_valid=True)
        for validator in self.validators:
            sub_result = validator.validate(data)
            if not sub_result.is_valid:
                result.is_valid = False
                result.errors.extend(sub_result.errors)
            result.warnings.extend(sub_result.warnings)
        return result

    def validate_file(self, file_path: str) -> ValidationResult:
        result = ValidationResult(is_valid=True)
        try:
            with open(file_path) as f:
                if file_path.endswith(".json"):
                    data = json.load(f)
                elif file_path.endswith(".csv"):
                    data = pd.read_csv(file_path)
                else:
                    result.is_valid = False
                    result.errors.append(f"Unsupported file type: {file_path}")
                    return result
                return self.validate(data)
        except FileNotFoundError:
            result.is_valid = False
            result.errors.append(f"File not found: {file_path}")
        except Exception as e:
            result.is_valid = False
            result.errors.append(f"Error reading file: {str(e)}")
        return result


def validate_sales_data(data: pd.DataFrame) -> ValidationResult:
    """Convenience function to validate sales data."""
    validator = SalesDataValidator()
    return validator.validate(data)


def validate_forecast(data: pd.DataFrame) -> ValidationResult:
    """Convenience function to validate forecast data."""
    validator = DemandForecastValidator()
    return validator.validate(data)
