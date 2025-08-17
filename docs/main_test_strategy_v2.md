# ModBuddy Comprehensive Testing Guide (v2)

## Required Tools & Libraries

To implement the ModBuddy testing strategy, install and use the following tools:

- **pytest**: Core test runner for Python, supports fixtures, parametrization, and plugins.
- **pytest-qt**: Simulates Qt UI events, widget interactions, and verifies UI state for PySide6 GUIs.
- **pytest-bdd**: Enables Gherkin-style, scenario-driven BDD tests for user workflows and edge cases.
- **pytest-check**: Allows non-blocking, multi-assertion tests for robust validation and actionable feedback.
- **pytest-metadata**: Enriches test reports with custom metadata for debugging and CI integration.
- **unittest.mock (MagicMock)**: Mocks dialogs, file operations, and external dependencies.
- **pytest monkeypatch**: Replaces functions, methods, and attributes at runtime for deterministic tests.
- **PySide6.QtTest (optional)**: For low-level event simulation if needed.

---

## Testing Strategy Overview

**Goals:**

- Ensure ModBuddy's UI and logic are robust, user-friendly, and error-resistant.
- Cover all major user flows, edge cases, and integration points.
- Enable rapid, reliable regression detection and future-proofing.

**Methodology:**

- Use a mix of unit, integration, functional, and BDD scenario tests.
- Simulate real user interactions (button clicks, dialog inputs, file selection).
- Isolate external dependencies using mocks and monkeypatching.
- Validate both UI state and underlying data/model changes.
- Test error handling and edge cases systematically.
- Enrich test reports with metadata for reproducibility and CI/CD.

---

## Test Patterns & Examples

### 1. UI Initialization & Smoke Tests

## Practical Examples: Good Tests & Tool Usage

Below are examples of high-quality tests and how each recommended tool is used in ModBuddy's test suite. These illustrate best practices for clarity, robustness, and maintainability.

### Example 1: UI Initialization Smoke Test (pytest, pytest-qt)

```python
def test_app_initialization(modbuddy_app):
    """Verify that the ModBuddy UI loads and is accessible."""
    app, window = modbuddy_app
    assert app is not None
    assert window is not None
    # Check that key widgets exist
    assert hasattr(window, "game_combobox")
    assert hasattr(window, "mod_list")
```

### Example 2: Simulating Dialogs and User Input (pytest, monkeypatch, MagicMock)

```python
def test_create_new_game(monkeypatch, modbuddy_app, tmp_path):
    """Test the new game creation flow with mocked dialogs."""
    app, window = modbuddy_app
    # Mock dialog responses
    monkeypatch.setattr("PySide6.QtWidgets.QFileDialog.getExistingDirectory", lambda *_: str(tmp_path / "game_folder"))
    monkeypatch.setattr("PySide6.QtWidgets.QInputDialog.getText", lambda *_: ("Test Game", True))
    # Mock filesystem operations if needed
    monkeypatch.setattr("modbuddy.modpack.ModPack.add_mod", lambda self: None)
    app.create_new_game()
    # Verify game preset file created
    assert (tmp_path / "games" / "Test Game.json").exists()
```

### Example 3: Error Handling and Edge Case Testing (pytest, monkeypatch)

```python
def test_add_mod_cancel(monkeypatch, modbuddy_app):
    """Test add_mod when user cancels the folder dialog."""
    app, window = modbuddy_app
    monkeypatch.setattr("PySide6.QtWidgets.QFileDialog.getExistingDirectory", lambda *_: "")
    app.add_mod(Path("."))
    # Verify no mod added, state unchanged
    assert "mods" not in app.game_setting or not app.game_setting["mods"]
```

### Example 4: UI State Verification (pytest-qt)

```python
def test_dirty_status(modbuddy_app):
    """Test that dirty status updates UI buttons."""
    app, window = modbuddy_app
    app.set_dirty_status(True)
    assert app.ui.initialize_mod.isEnabled()
    assert app.ui.save_profile_button.isEnabled()
    app.set_dirty_status(False)
    assert not app.ui.initialize_mod.isEnabled()
    assert not app.ui.save_profile_button.isEnabled()
```

### Example 5: BDD Scenario Test (pytest-bdd)

```python
from pytest_bdd import scenario, given, when, then, parsers

@scenario('features/create_game.feature', 'User creates a new game')
def test_create_game():
    pass

@given(parsers.parse("the user is on the main screen"))
def main_screen(modbuddy_app):
    app, window = modbuddy_app
    # ... setup code ...

@when(parsers.parse("the user creates a new game named '{game_name}'"))
def create_game(monkeypatch, modbuddy_app, game_name, tmp_path):
    monkeypatch.setattr("PySide6.QtWidgets.QInputDialog.getText", lambda *_: (game_name, True))
    # ... simulate dialog ...

@then(parsers.parse("the game preset file should exist"))
def verify_game_file(tmp_path, game_name):
    assert (tmp_path / "games" / f"{game_name}.json").exists()
```

### Example 6: Non-blocking Assertions (pytest-check)

```python
from pytest_check import check

def test_mod_list_state(modbuddy_app):
    app, window = modbuddy_app
    mods = app.get_mods()
    check.equal(len(mods), 5, "Should have 5 mods loaded")
    check.is_in("AwesomeMod", [m.name for m in mods], "AwesomeMod should be present")
    check.is_not_in("BrokenMod", [m.name for m in mods], "BrokenMod should not be present")
```

### Example 7: Metadata in Test Reports (pytest-metadata)

```python
def test_metadata(metadata):
    assert 'metadata' in metadata['Plugins']
    assert metadata['Platform'].startswith('Windows')
```

### Example 8: Accessibility & Usability (pytest-qt, keyboard simulation)

```python
def test_keyboard_navigation(qtbot, modbuddy_app):
    app, window = modbuddy_app
    qtbot.keyClick(window.game_combobox, 'Tab')
    assert window.game_combobox.hasFocus()
```

---

## How These Tools Work Together

- **pytest** runs all tests, manages fixtures, and integrates plugins.
- **pytest-qt** simulates user events and verifies UI state for PySide6 GUIs.
- **pytest-bdd** enables scenario-driven tests for user workflows and edge cases.
- **pytest-check** allows multiple assertions per test, reporting all failures for actionable feedback.
- **pytest-metadata** enriches test reports with environment, game, and CI context.
- **monkeypatch & MagicMock** isolate external dependencies for deterministic, reliable tests.

By combining these tools, ModBuddy's test suite achieves high coverage, rapid regression detection, and maintainable, future-proof quality assurance.

### 2. Game & Profile Management

- Test creating a new game (simulate dialog input, verify file creation, check UI updates).
- Test loading, saving, duplicating, and switching profiles.
- Test updating game/profile comboboxes and last activity tracking.

### 3. Mod Management

- Test adding mods from folders and archives (simulate file dialogs, verify mod list updates).
- Test editing, toggling, moving, and removing mods in the table.
- Test FOMOD parsing and handling (simulate mod folders with FOMOD configs).

### 4. Source Management

- Test adding, exporting, downloading, and updating sources.
- Test source table interactions and error handling for invalid sources.

### 5. Filesystem Operations

- Test cleaning mod folders, initializing mods, and writing presets/configs.
- Inject errors (permission denied, missing files) and verify error dialogs.

### 6. UI State & Dirty Status

- Test dirty status tracking and UI feedback.
- Test state transitions when mods/games/profiles are changed.

### 7. Error Handling & Edge Cases

- Test invalid user input (empty names, bad paths).
- Test corrupted config files, missing UI files, and unexpected exceptions.
- Test all QMessageBox dialogs for correct user feedback.

### 8. Integration & Regression

- Test full user flows: create game → add mod → save profile → switch game.
- Test that all changes persist across app restarts.

### 9. Accessibility & Usability

- Test keyboard navigation, focus order, and accessibility labels.
- Test that all interactive elements are reachable and operable.

### 10. Performance & Scalability

- Test with large numbers of mods, profiles, and sources.
- Test responsiveness and memory usage under load.

---

## Best Practices

- **Isolate Tests**: Use fixtures and tmp_path to avoid polluting the real filesystem.
- **Mock External Dependencies**: Always monkeypatch dialogs, file operations, and network calls.
- **Test Both Success and Failure Paths**: For every user flow, test both the happy path and error/edge cases.
- **Use Protocols for UI Mocks**: Type-safe access to widgets ensures maintainability.
- **Keep Tests Deterministic**: Avoid reliance on timing, real user input, or external state.
- **Document Test Intent**: Use clear docstrings and comments to explain what each test verifies.
- **Leverage BDD for User Flows**: Write Gherkin feature files for major workflows and edge cases.
- **Use pytest-check for Robust Assertions**: Report all failures in a test for actionable feedback.
- **Enrich Reports with pytest-metadata**: Track environment, game, modpack, and CI context.

---

## Implementation Recommendations

- Structure tests by feature (game, mod, source, profile).
- Write both unit and integration tests for critical flows.
- Use pytest-bdd for scenario-driven tests, pytest-check for robust assertions, and pytest-metadata for rich reporting.
- Ensure tests are deterministic and do not depend on real filesystem state.
- Integrate with CI/CD for automated regression and reporting.

---

## References

- [pytest documentation](https://docs.pytest.org/en/stable/)
- [pytest-qt documentation](https://pytest-qt.readthedocs.io/en/latest/)
- [pytest-bdd documentation](https://pytest-bdd.readthedocs.io/en/latest/)
- [pytest-check documentation](https://github.com/okken/pytest-check)
- [pytest-metadata documentation](https://github.com/pytest-dev/pytest-metadata)
- [unittest.mock documentation](https://docs.python.org/3/library/unittest.mock.html)
- [PySide6 documentation](https://doc.qt.io/qtforpython/)

---

## Summary

This guide provides a comprehensive, example-driven approach for testing ModBuddy's UI and logic. By following these patterns and using the recommended tools, both humans and LLMs can generate robust, maintainable tests that ensure ModBuddy's quality and reliability. Integrate BDD, non-blocking assertions, and rich metadata to future-proof your test suite and streamline development.
