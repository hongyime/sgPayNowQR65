import contextlib
import io
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

from download_path_manager import _validate_and_create_path


class TestOutputDirectoryValidation(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name).resolve()
        self.output = self.root / 'output'
        self.output.mkdir()

    def test_existing_probe_name_is_preserved(self) -> None:
        existing = self.output / '.write_test_temp'
        original = b'Preserve this synthetic retained file.\x00\xff'
        existing.write_bytes(original)

        self.assertEqual(_validate_and_create_path(str(self.output), 'test'), str(self.output))

        self.assertTrue(existing.is_file(), 'Validation must not delete a pre-existing file')
        self.assertEqual(existing.read_bytes(), original)
        self.assertEqual(list(self.output.iterdir()), [existing])

    def test_existing_directory_named_like_probe_is_not_a_write_failure(self) -> None:
        existing = self.output / '.write_test_temp'
        existing.mkdir()
        retained = existing / 'retained.bin'
        retained.write_bytes(b'synthetic retained bytes')

        self.assertEqual(_validate_and_create_path(str(self.output), 'test'), str(self.output))

        self.assertEqual(retained.read_bytes(), b'synthetic retained bytes')
        self.assertEqual(list(self.output.iterdir()), [existing])

    def test_success_leaves_no_probe_files(self) -> None:
        self.assertEqual(_validate_and_create_path(str(self.output), 'test'), str(self.output))
        self.assertEqual(list(self.output.iterdir()), [])

    def test_existing_file_is_not_treated_as_a_directory(self) -> None:
        existing = self.output / 'retained.bin'
        existing.write_bytes(b'synthetic retained bytes')
        with self.assertRaises(FileExistsError):
            _validate_and_create_path(str(existing), 'test')
        self.assertEqual(existing.read_bytes(), b'synthetic retained bytes')

    def test_declined_directory_is_not_created(self) -> None:
        requested = self.root / 'declined'
        with patch('builtins.input', return_value='n'), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(ValueError, 'creation declined'):
                _validate_and_create_path(str(requested), 'test')
        self.assertFalse(requested.exists())

    def test_confirmed_directory_is_created_without_probe_artifacts(self) -> None:
        requested = self.root / 'confirmed'
        with patch('builtins.input', return_value='y'), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(_validate_and_create_path(str(requested), 'test'), str(requested))
        self.assertTrue(requested.is_dir())
        self.assertEqual(list(requested.iterdir()), [])

    def test_concurrent_validations_preserve_existing_files(self) -> None:
        existing = self.output / '.write_test_temp'
        existing.write_bytes(b'synthetic retained bytes')
        with ThreadPoolExecutor(max_workers=4) as workers:
            results = list(workers.map(lambda _: _validate_and_create_path(str(self.output), 'test'), range(16)))
        self.assertEqual(results, [str(self.output)] * 16)
        self.assertEqual(existing.read_bytes(), b'synthetic retained bytes')
        self.assertEqual(list(self.output.iterdir()), [existing])

    def test_denied_probe_creation_is_reported_without_mutating_existing_files(self) -> None:
        existing = self.output / '.write_test_temp'
        existing.write_bytes(b'synthetic retained bytes')
        with patch('download_path_manager.tempfile.NamedTemporaryFile', side_effect=PermissionError('synthetic denial')):
            with self.assertRaisesRegex(PermissionError, 'No write permission'):
                _validate_and_create_path(str(self.output), 'test')
        self.assertEqual(existing.read_bytes(), b'synthetic retained bytes')
        self.assertEqual(list(self.output.iterdir()), [existing])

    def test_failed_probe_write_is_reported_and_only_its_own_probe_is_removed(self) -> None:
        existing = self.output / '.write_test_temp'
        existing.write_bytes(b'synthetic retained bytes')
        create_probe = tempfile.NamedTemporaryFile

        def failing_probe(*args: Any, **kwargs: Any) -> Any:
            probe = create_probe(*args, **kwargs)
            probe.write = Mock(side_effect=OSError('synthetic full disk'))
            return probe

        with patch('download_path_manager.tempfile.NamedTemporaryFile', side_effect=failing_probe):
            with self.assertRaisesRegex(Exception, 'synthetic full disk'):
                _validate_and_create_path(str(self.output), 'test')
        self.assertEqual(existing.read_bytes(), b'synthetic retained bytes')
        self.assertEqual(list(self.output.iterdir()), [existing])

    def test_preexisting_symlink_and_its_target_are_preserved(self) -> None:
        target = self.root / 'retained.bin'
        target.write_bytes(b'synthetic retained bytes outside the output folder')
        existing = self.output / '.write_test_temp'
        try:
            existing.symlink_to(target)
        except (OSError, NotImplementedError) as error:
            self.skipTest(f'Symlink creation is unavailable: {type(error).__name__}')
        self.assertEqual(_validate_and_create_path(str(self.output), 'test'), str(self.output))
        self.assertTrue(existing.is_symlink())
        self.assertEqual(target.read_bytes(), b'synthetic retained bytes outside the output folder')
        self.assertEqual(list(self.output.iterdir()), [existing])


if __name__ == '__main__':
    unittest.main()
