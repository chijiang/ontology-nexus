"""
Tests for cron expression validation and parsing functionality.

This module tests the cron expression validation that is used
by the scheduled task schemas and services.
"""

import pytest
from datetime import datetime

from app.schemas.scheduled_task import (
    ScheduledTaskCreate,
    ScheduledTaskUpdate,
    CronTemplate,
    CronTemplateTypeEnum,
)


class TestCronExpressionValidation:
    """Tests for cron expression validation in schemas."""

    def test_validate_standard_cron_expressions(self):
        """Test validation of standard 5-part cron expressions."""
        valid_expressions = [
            "*/5 * * * *",  # Every 5 minutes
            "0 * * * *",  # Every hour
            "0 0 * * *",  # Daily at midnight
            "0 0 * * 0",  # Weekly on Sunday
            "0 0 1 * *",  # Monthly on 1st
            "0 9-17 * * 1-5",  # Every hour 9-17 on weekdays
            "30 8,12,18 * * *",  # At 8:30, 12:30, 18:30
            "0 0,12 1 */2 *",  # At midnight and noon on 1st of every other month
        ]

        for expr in valid_expressions:
            task = ScheduledTaskCreate(
                task_type="sync",
                task_name=f"Test {expr}",
                target_id=1,
                cron_expression=expr,
            )
            assert task.cron_expression == expr

    def test_validate_extended_cron_expressions(self):
        """Test validation of extended 6-7 part cron expressions."""
        valid_expressions = [
            "*/5 * * * * *",  # Every 5 seconds
            "0 * * * * *",  # Every minute (with seconds field)
            "0 0 * * * 0",  # Weekly with 6 fields
            "0 0 * * * 0 2024",  # Weekly in 2024
        ]

        for expr in valid_expressions:
            task = ScheduledTaskCreate(
                task_type="sync",
                task_name=f"Test {expr}",
                target_id=1,
                cron_expression=expr,
            )
            assert task.cron_expression == expr

    def test_validate_invalid_cron_expressions(self):
        """Test that invalid cron expressions are rejected."""
        # Only test expressions that fail the part count validation
        # (Value validation like "60" for minutes is done by APScheduler, not Pydantic)
        invalid_expressions = [
            "* * * *",  # Only 4 parts
            "* * * * * * * * *",  # Too many parts
            "invalid",  # Not a valid cron expression (1 part)
        ]

        for expr in invalid_expressions:
            with pytest.raises(ValueError, match="Cron expression must have 5-7 parts"):
                ScheduledTaskCreate(
                    task_type="sync",
                    task_name="Invalid Test",
                    target_id=1,
                    cron_expression=expr,
                )

    def test_validate_empty_cron_expression(self):
        """Test that empty cron expression is rejected by min_length validator."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            ScheduledTaskCreate(
                task_type="sync",
                task_name="Empty Test",
                target_id=1,
                cron_expression="",
            )

    def test_validate_cron_in_update_schema(self):
        """Test cron validation in update schema."""
        # Valid expression should pass
        task_update = ScheduledTaskUpdate(cron_expression="0 * * * *")
        assert task_update.cron_expression == "0 * * * *"

        # Invalid expression should fail
        with pytest.raises(ValueError, match="Cron expression must have 5-7 parts"):
            ScheduledTaskUpdate(cron_expression="* * * *")

        # None should be allowed for update
        task_update_none = ScheduledTaskUpdate(cron_expression=None)
        assert task_update_none.cron_expression is None


class TestCronTemplateSchemas:
    """Tests for cron template schemas."""

    def test_cron_template_interval_type(self):
        """Test interval template type."""
        template = CronTemplate(
            name="Every 5 minutes",
            type=CronTemplateTypeEnum.INTERVAL,
            expression="*/5 * * * *",
            description="Run every 5 minutes",
            example="0, 5, 10, 15...",
        )
        assert template.type == "interval"
        assert template.expression == "*/5 * * * *"

    def test_cron_template_specific_type(self):
        """Test specific template type."""
        template = CronTemplate(
            name="Daily at 2 AM",
            type=CronTemplateTypeEnum.SPECIFIC,
            expression="0 2 * * *",
            description="Run daily at 2:00 AM",
            example="Daily at 2:00 AM",
        )
        assert template.type == "specific"

    def test_cron_template_advanced_type(self):
        """Test advanced template type."""
        template = CronTemplate(
            name="Complex schedule",
            type=CronTemplateTypeEnum.ADVANCED,
            expression="*/5 9-17 * * 1-5",
            description="Every 5 minutes on weekdays between 9-17",
            example="9:00, 9:05, 9:10... until 17:00 on Mon-Fri",
        )
        assert template.type == "advanced"


class TestCronExpressionExamples:
    """Tests for common cron expression examples."""

    @pytest.mark.parametrize(
        "expression,description",
        [
            ("* * * * *", "Every minute"),
            ("*/5 * * * *", "Every 5 minutes"),
            ("0 * * * *", "Every hour"),
            ("0 0 * * *", "Every day at midnight"),
            ("0 0 * * 0", "Every Sunday at midnight"),
            ("0 0 * * 1", "Every Monday at midnight"),
            ("0 0 1 * *", "First day of every month"),
            ("0 0 1 1 *", "January 1st every year"),
            ("0 6,18 * * *", "Twice daily at 6 AM and 6 PM"),
            ("0 9-17 * * 1-5", "Every hour 9-17 on weekdays"),
            ("*/10 * * * *", "Every 10 minutes"),
            ("0 */2 * * *", "Every 2 hours"),
            ("0 0,12 * * *", "Daily at midnight and noon"),
            ("15 3 * * 1-5", "Weekdays at 3:15 AM"),
            ("0 0 1,15 * *", "1st and 15th of month"),
        ],
    )
    def test_common_cron_expressions(self, expression, description):
        """Test that common cron expressions are valid."""
        task = ScheduledTaskCreate(
            task_type="sync",
            task_name=description,
            target_id=1,
            cron_expression=expression,
        )
        assert task.cron_expression == expression

    def test_cron_expression_with_special_characters(self):
        """Test cron expressions with special characters."""
        # Asterisk (any value)
        task = ScheduledTaskCreate(
            task_type="sync",
            task_name="Asterisk test",
            target_id=1,
            cron_expression="* * * * *",
        )
        assert task.cron_expression == "* * * * *"

        # Slash (step values)
        task = ScheduledTaskCreate(
            task_type="sync",
            task_name="Slash test",
            target_id=1,
            cron_expression="*/15 * * * *",
        )
        assert task.cron_expression == "*/15 * * * *"

        # Hyphen (ranges)
        task = ScheduledTaskCreate(
            task_type="sync",
            task_name="Hyphen test",
            target_id=1,
            cron_expression="0 9-17 * * *",
        )
        assert task.cron_expression == "0 9-17 * * *"

        # Comma (multiple values)
        task = ScheduledTaskCreate(
            task_type="sync",
            task_name="Comma test",
            target_id=1,
            cron_expression="0 9,12,15 * * *",
        )
        assert task.cron_expression == "0 9,12,15 * * *"


class TestCronEdgeCases:
    """Tests for edge cases in cron expressions."""

    def test_cron_with_whitespace(self):
        """Test that expressions with extra whitespace are handled."""
        # This should still work - the split() handles whitespace
        task = ScheduledTaskCreate(
            task_type="sync",
            task_name="Whitespace test",
            target_id=1,
            cron_expression="  0  *  *  *  *  ",
        )
        # Note: The validator only checks part count, not whitespace
        assert len(task.cron_expression.strip().split()) == 5

    def test_cron_minimum_expression(self):
        """Test minimum valid cron expression (5 parts)."""
        task = ScheduledTaskCreate(
            task_type="sync",
            task_name="Minimum test",
            target_id=1,
            cron_expression="* * * * *",
        )
        assert len(task.cron_expression.split()) == 5

    def test_cron_maximum_expression(self):
        """Test maximum valid cron expression (7 parts)."""
        task = ScheduledTaskCreate(
            task_type="sync",
            task_name="Maximum test",
            target_id=1,
            cron_expression="* * * * * * 2024",
        )
        assert len(task.cron_expression.split()) == 7

    def test_cron_exceeds_maximum(self):
        """Test that 8-part expression is rejected."""
        with pytest.raises(ValueError, match="Cron expression must have 5-7 parts"):
            ScheduledTaskCreate(
                task_type="sync",
                task_name="Too many parts",
                target_id=1,
                cron_expression="* * * * * * * *",
            )

    def test_cron_below_minimum(self):
        """Test that 4-part expression is rejected."""
        with pytest.raises(ValueError, match="Cron expression must have 5-7 parts"):
            ScheduledTaskCreate(
                task_type="sync",
                task_name="Too few parts",
                target_id=1,
                cron_expression="* * * *",
            )


class TestCronValidationMessages:
    """Tests for validation error messages."""

    def test_empty_expression_error_message(self):
        """Test error message for empty expression."""
        # Empty string is caught by min_length validator, not cron validator
        with pytest.raises(Exception):  # Pydantic ValidationError
            ScheduledTaskCreate(
                task_type="sync",
                task_name="Empty test",
                target_id=1,
                cron_expression="",
            )

    def test_too_few_parts_error_message(self):
        """Test error message for too few parts."""
        with pytest.raises(ValueError, match="Cron expression must have 5-7 parts"):
            ScheduledTaskCreate(
                task_type="sync",
                task_name="Few parts test",
                target_id=1,
                cron_expression="* * *",
            )

    def test_too_many_parts_error_message(self):
        """Test error message for too many parts."""
        with pytest.raises(ValueError, match="Cron expression must have 5-7 parts"):
            ScheduledTaskCreate(
                task_type="sync",
                task_name="Many parts test",
                target_id=1,
                cron_expression="* * * * * * * * * *",
            )


class TestCronPredefinedExpressions:
    """Tests for predefined/special cron expressions."""

    def test_yearly_expression(self):
        """Test yearly (@yearly or @annually) equivalent."""
        # Standard cron for yearly: at midnight on Jan 1
        task = ScheduledTaskCreate(
            task_type="sync",
            task_name="Yearly",
            target_id=1,
            cron_expression="0 0 1 1 *",
        )
        assert task.cron_expression == "0 0 1 1 *"

    def test_monthly_expression(self):
        """Test monthly equivalent."""
        # Standard cron for monthly: at midnight on 1st of month
        task = ScheduledTaskCreate(
            task_type="sync",
            task_name="Monthly",
            target_id=1,
            cron_expression="0 0 1 * *",
        )
        assert task.cron_expression == "0 0 1 * *"

    def test_weekly_expression(self):
        """Test weekly equivalent."""
        # Standard cron for weekly: at midnight on Sunday (0)
        task = ScheduledTaskCreate(
            task_type="sync",
            task_name="Weekly",
            target_id=1,
            cron_expression="0 0 * * 0",
        )
        assert task.cron_expression == "0 0 * * 0"

    def test_daily_expression(self):
        """Test daily equivalent."""
        # Standard cron for daily: at midnight
        task = ScheduledTaskCreate(
            task_type="sync",
            task_name="Daily",
            target_id=1,
            cron_expression="0 0 * * *",
        )
        assert task.cron_expression == "0 0 * * *"

    def test_hourly_expression(self):
        """Test hourly equivalent."""
        # Standard cron for hourly: at minute 0
        task = ScheduledTaskCreate(
            task_type="sync",
            task_name="Hourly",
            target_id=1,
            cron_expression="0 * * * *",
        )
        assert task.cron_expression == "0 * * * *"
