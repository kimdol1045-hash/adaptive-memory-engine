import json
import subprocess

from ame.security import MacOSKeychainTokenVault, PrivateFileTokenVault, redact_pii


class FakeSecurityRunner:
    def __init__(self) -> None:
        self.secret = ""

    def __call__(self, args: list[str], text: bool, capture_output: bool, check: bool) -> subprocess.CompletedProcess[str]:
        if args[1] == "find-generic-password":
            if not self.secret:
                return subprocess.CompletedProcess(args, 44, "", "not found")
            return subprocess.CompletedProcess(args, 0, self.secret, "")
        if args[1] == "add-generic-password":
            self.secret = args[args.index("-w") + 1]
            return subprocess.CompletedProcess(args, 0, "", "")
        if args[1] == "delete-generic-password":
            self.secret = ""
            return subprocess.CompletedProcess(args, 0, "", "")
        raise AssertionError(args)


def test_private_file_token_vault_roundtrip_and_delete(tmp_path):
    path = tmp_path / "tokens" / "provider.json"
    vault = PrivateFileTokenVault(path)

    vault.save({"id": {"access_token": "secret"}})

    assert vault.load()["id"]["access_token"] == "secret"
    assert path.exists()
    vault.delete()
    assert vault.load() == {}


def test_macos_keychain_token_vault_roundtrip_with_fake_runner():
    runner = FakeSecurityRunner()
    vault = MacOSKeychainTokenVault("adaptive-memory-engine.test", runner=runner)

    vault.save({"id": {"access_token": "secret"}})

    assert json.loads(runner.secret)["id"]["access_token"] == "secret"
    assert vault.load()["id"]["access_token"] == "secret"
    vault.delete()
    assert vault.load() == {}


def test_redact_pii_replaces_emails_and_phone_numbers():
    payload = {
        "participants": ["alice@example.com", "andan@example.com"],
        "body": "Call +1 555-010-9999 or email alice@example.com.",
    }

    assert redact_pii(payload) == {
        "participants": ["[email]", "[email]"],
        "body": "Call [phone] or email [email].",
    }
