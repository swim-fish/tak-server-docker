"""Verify endpoint arguments and generated artifacts without issuing real credentials."""
import contextlib
import io
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bootstrap_local as bootstrap


class BootstrapEndpointTests(unittest.TestCase):
    def test_invalid_arguments_stop_before_runtime_changes(self):
        cases = [[], ['--force'], ['--host', ''], ['--ip', ' '],
                 ['--dns', 'https://takbox.local'], ['--host', '192.168.137.1'],
                 ['--ip', 'takbox.local'], ['--ip', '192.168.137.999']]
        for args in cases:
            with self.subTest(args=args), patch.object(sys, 'argv', ['bootstrap', *args]), \
                 patch.object(bootstrap.shutil, 'which') as which, \
                 patch.object(bootstrap.shutil, 'rmtree') as remove, \
                 contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    bootstrap.main()
                self.assertEqual(error.exception.code, 2)
                which.assert_not_called()
                remove.assert_not_called()

    def test_generation_modes(self):
        cases = [
            (['--dns', 'takbox.local'], 'DNS:takbox.local', 'takbox.local', True, False),
            (['--ip', '192.168.137.1'], 'IP:192.168.137.1', '192.168.137.1', False, True),
            (['--host', 'takbox.local', '--ip', '192.168.137.1'],
             'DNS:takbox.local,IP:192.168.137.1', 'takbox.local', True, True),
        ]
        for args, san, endpoint, check_dns, check_ip in cases:
            with self.subTest(args=args), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                runtime = root / 'runtime'
                upstream = root / 'vendor'
                (upstream / 'tak').mkdir(parents=True)
                (upstream / 'tak/CoreConfig.example.xml').write_text('<config><auth></auth></config>')
                paths = {'PROJECT': root, 'UPSTREAM': upstream, 'RUNTIME': runtime,
                         'SECRETS': runtime / 'secrets', 'PRIVATE': runtime / 'pki/private',
                         'PUBLIC': runtime / 'pki/public', 'CA_DB': runtime / 'pki/private/ca-db',
                         'ROOT_CA_DB': runtime / 'pki/private/root-ca-db',
                         'TAK_CERTS': runtime / 'tak/certs', 'PACKAGES': runtime / 'packages'}
                calls = []

                def fake_run(*command, **kwargs):
                    calls.append(command)
                    for flag in ('-out', '-keystore', '-destkeystore'):
                        if flag in command:
                            target = Path(command[command.index(flag) + 1])
                            target.parent.mkdir(parents=True, exist_ok=True)
                            target.write_text('test fixture\n')

                with patch.multiple(bootstrap, **paths), \
                     patch.object(bootstrap, 'run', side_effect=fake_run), \
                     patch.object(bootstrap, 'write_identity'), \
                     patch.object(bootstrap.shutil, 'which', side_effect=lambda name: name), \
                     patch.object(sys, 'argv', ['bootstrap', *args]), \
                     contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(bootstrap.main(), 0)
                for name in ('takserver', 'mumble'):
                    ext = (paths['PRIVATE'] / f'{name}.ext').read_text()
                    self.assertIn(f'subjectAltName={san}\n', ext)
                    requests = [c for c in calls if 'req' in c and str(paths['PRIVATE'] / f'{name}.csr.pem') in c]
                    self.assertEqual(len(requests), 1)
                    self.assertTrue(requests[0][requests[0].index('-subj') + 1].endswith('/CN=' + endpoint))
                    cert = str(paths['PUBLIC'] / f'{name}.crt.pem')
                    checks = [c for c in calls if 'verify' in c and cert in c]
                    self.assertEqual(any('-verify_hostname' in c for c in checks), check_dns)
                    self.assertEqual(any('-verify_ip' in c for c in checks), check_ip)
                with zipfile.ZipFile(paths['PACKAGES'] / 'atak-local-test.dpk') as package:
                    prefs = ElementTree.fromstring(package.read('config/servers.pref'))
                    self.assertEqual(prefs.find(".//entry[@key='connectString0']").text, endpoint + ':8089:ssl')


if __name__ == '__main__':
    unittest.main()
