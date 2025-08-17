
# ModBuddy UI Testing Strategy & Tooling Guide

## 1. Testing Strategy Overview

**Goals:**

- Ensure ModBuddy's UI and logic are robust, user-friendly, and error-resistant.
- Cover all major user flows, edge cases, and integration points.
- Enable rapid, reliable regression detection and future-proofing.

**Methodology:**

- Use a mix of unit, integration, and functional tests.
- Simulate real user interactions (button clicks, dialog inputs, file selection).
- Isolate external dependencies (filesystem, dialogs) using mocks and monkeypatching.
- Validate both UI state and underlying data/model changes.
- Test error handling and edge cases systematically.

## 2. Recommended Tools

- **pytest**: Core test runner, supports fixtures, parametrization, and rich reporting.
- **pytest-qt**: For simulating Qt UI events, widget interactions, and verifying UI state.
- **unittest.mock (MagicMock)**: For mocking dialogs, file operations, and external dependencies.
- **pytest monkeypatch**: For replacing functions, methods, and attributes at runtime.
- **PySide6.QtTest (optional)**: For low-level event simulation if needed.

## 3. Test Patterns & Examples

### Example 1: UI Initialization Smoke Test

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

### Example 2: Simulating Dialogs and User Input

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

### Example 3: Error Handling and Edge Case Testing

```python
def test_add_mod_cancel(monkeypatch, modbuddy_app):
    """Test add_mod when user cancels the folder dialog."""
    app, window = modbuddy_app
    monkeypatch.setattr("PySide6.QtWidgets.QFileDialog.getExistingDirectory", lambda *_: "")
    app.add_mod(Path("."))
    # Verify no mod added, state unchanged
    assert "mods" not in app.game_setting or not app.game_setting["mods"]
```

### Example 4: UI State Verification

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

## 4. Best Practices

- **Isolate Tests**: Use fixtures and tmp_path to avoid polluting the real filesystem.
- **Mock External Dependencies**: Always monkeypatch dialogs, file operations, and network calls.
- **Test Both Success and Failure Paths**: For every user flow, test both the happy path and error/edge cases.
- **Use Protocols for UI Mocks**: Type-safe access to widgets ensures maintainability.
- **Keep Tests Deterministic**: Avoid reliance on timing, real user input, or external state.
- **Document Test Intent**: Use clear docstrings and comments to explain what each test verifies.

## 5. LLM Guidance

- When generating tests, always:
  - Simulate user actions using pytest-qt or monkeypatching.
  - Mock dialogs and file operations for deterministic results.
  - Assert both UI state and underlying data changes.
  - Cover edge cases, error handling, and integration flows.
  - Use fixtures for setup and teardown.

---

## 6. References

- [pytest documentation](https://docs.pytest.org/en/stable/)
- [pytest-qt documentation](https://pytest-qt.readthedocs.io/en/latest/)
- [unittest.mock documentation](https://docs.python.org/3/library/unittest.mock.html)
- [PySide6 documentation](https://doc.qt.io/qtforpython/)

---

## 7. Summary

This guide provides a comprehensive, example-driven approach for testing ModBuddy's UI and logic. By following these patterns and using the recommended tools, both humans and LLMs can generate robust, maintainable tests that ensure ModBuddy's quality and reliability.

## Comprehensive ModBuddy UI Testing Strategy

### 1. **UI Initialization & Smoke Tests**

- Test that the main window loads without errors.
- Verify all expected widgets are present and accessible via the protocol.
- Ensure the app can start and exit cleanly.

### 2. **Game & Profile Management**

- Test creating a new game (simulate dialog input, verify file creation, check UI updates).
- Test loading, saving, duplicating, and switching profiles.
- Test updating game/profile comboboxes and last activity tracking.

### 3. **Mod Management**

- Test adding mods from folders and archives (simulate file dialogs, verify mod list updates).
- Test editing, toggling, moving, and removing mods in the table.
- Test FOMOD parsing and handling (simulate mod folders with FOMOD configs).

### 4. **Source Management**

- Test adding, exporting, downloading, and updating sources.
- Test source table interactions and error handling for invalid sources.

### 5. **Filesystem Operations**

- Test cleaning mod folders, initializing mods, and writing presets/configs.
- Inject errors (permission denied, missing files) and verify error dialogs.

### 6. **UI State & Dirty Status**

- Test dirty status tracking and UI feedback.
- Test state transitions when mods/games/profiles are changed.

### 7. **Error Handling & Edge Cases**

- Test invalid user input (empty names, bad paths).
- Test corrupted config files, missing UI files, and unexpected exceptions.
- Test all QMessageBox dialogs for correct user feedback.

### 8. **Integration & Regression**

- Test full user flows: create game → add mod → save profile → switch game.
- Test that all changes persist across app restarts.

### 9. **Accessibility & Usability**

- Test keyboard navigation, focus order, and accessibility labels (if possible).
- Test that all interactive elements are reachable and operable.

### 10. **Performance & Scalability**

- Test with large numbers of mods, profiles, and sources.
- Test responsiveness and memory usage under load.

---

## Test Implementation Recommendations

- Use pytest-qt and MagicMock to simulate UI and filesystem.
- Use monkeypatching for dialogs, file operations, and external dependencies.
- Structure tests by feature (game, mod, source, profile).
- Write both unit and integration tests for critical flows.
- Ensure tests are deterministic and do not depend on real filesystem state.
