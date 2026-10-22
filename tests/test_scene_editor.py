"""Portable saved-scene contract, without browser/device/model dependencies."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest
import json
import threading
import urllib.request
import urllib.error
from tools.tabletop.editor.settings import FIELDS

spec = importlib.util.spec_from_file_location('scene_editor_server', Path(__file__).resolve().parents[1] / 'tools/tabletop/editor/server.py')
editor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(editor)


class SceneProfileTests(unittest.TestCase):
    def setUp(self):
        self.profile = dict(version=1, system='snes', tv='panasonic', viewport=dict(width=720, height=480),
                            camera=dict(position=[178.5, 547.4, 1358.3], target=[178.5, -26.4, 69.6], fov=40),
                            objects={name: dict(position=[0, 0, 0], rotation=[0, 0, 0])
                                     for name in editor.NAMES})

    def test_authored_camera_and_rotations_roundtrip(self):
        self.profile['objects']['cart3'] = dict(position=[-100, 10.25, 330], rotation=[-90, 273, 12])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'layout.scene'
            path.write_text(editor.native_text(self.profile))
            self.assertEqual(editor.read_profile(path), self.profile)

    def test_viewport_key_order_has_no_effect(self):
        value = copy.deepcopy(self.profile)
        value['viewport'] = dict(height=480, width=720)
        self.assertEqual(editor.native_text(value), editor.native_text(self.profile))

    def test_invalid_camera_never_serializes(self):
        for field, value in [('position', [float('nan'), 0, 0]), ('fov', float('inf')), ('target', [10001, 0, 0])]:
            with self.subTest(field=field):
                profile = copy.deepcopy(self.profile)
                profile['camera'][field] = value
                with self.assertRaises(ValueError):
                    editor.native_text(profile)

    def test_missing_or_unexpected_objects_rejected(self):
        for name in ['cart7', 'arbitrary-file']:
            profile = copy.deepcopy(self.profile)
            if name == 'cart7':
                del profile['objects'][name]
            else:
                profile['objects'][name] = dict(position=[0, 0, 0], rotation=[0, 0, 0])
            with self.assertRaises(ValueError):
                editor.validate(profile)

    def test_43_keeps_exact_authored_values(self):
        self.profile['viewport']['height'] = 540
        self.profile['camera']['fov'] = 44.5
        validated = editor.validate(self.profile)
        self.assertEqual(validated['camera'], self.profile['camera'])
        self.assertIn('viewport 720 540\n', editor.native_text(validated))

    def test_eight_cart_upgrade_preserves_all_authored_values(self):
        old = copy.deepcopy(self.profile)
        old['objects'] = {name: node for name, node in old['objects'].items() if name in editor.NAMES[:12]}
        old['objects']['cart0']['position'] = [-398.33, 10.034, 684.159]
        before = copy.deepcopy(old)
        upgraded = editor.expand_profile(old)
        self.assertEqual(old, before)
        self.assertEqual(upgraded['camera'], before['camera'])
        self.assertEqual(upgraded['viewport'], before['viewport'])
        for name, node in before['objects'].items():
            self.assertEqual(upgraded['objects'][name], node)
        self.assertEqual(set(upgraded['objects']), set(editor.NAMES))
        self.assertEqual(len({tuple(upgraded['objects'][f'cart{i}']['position']) for i in range(8, 12)}), 4)
        self.assertEqual(editor.expand_profile(upgraded), upgraded)

    def test_legacy_native_roundtrip_stays_eight_carts(self):
        self.profile['objects'] = {name: self.profile['objects'][name] for name in editor.NAMES[:12]}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'layout.scene'
            path.write_text(editor.native_text(self.profile))
            self.assertEqual(editor.read_profile(path), self.profile)

    def test_console_profiles_have_their_own_files(self):
        for system in ('n64', 'nes'):
            profile = copy.deepcopy(self.profile)
            profile['system'] = system
            self.assertEqual(editor.validate(profile)['system'], system)
            self.assertEqual(editor.saved_path(system).name, system + '-panasonic.json')
            self.assertEqual(editor.native_path(system).name, system + '-panasonic.scene')
        self.assertEqual(editor.saved_path('snes'), editor.SAVED)
        profile = copy.deepcopy(self.profile)
        profile['system'] = 'dreamcast'
        with self.assertRaises(ValueError):
            editor.validate(profile)
        self.assertEqual(editor.query_system(''), 'snes')
        self.assertEqual(editor.query_system('system=nes'), 'nes')
        with self.assertRaises(ValueError):
            editor.query_system('system=../snes')

    def test_snes_layout_adopted_like_the_renderer(self):
        bottoms = dict(snes=-36.0, n64=-36.5, nes=-72.0)
        media = dict(snes=-10.0, nes=-9.5)
        original, original_media = editor.console_bottom, editor.media_bottom
        editor.console_bottom, editor.media_bottom = bottoms.get, media.get
        try:
            self.profile['objects']['console'] = dict(position=[-89.1, 48.93, 399.85], rotation=[0, -27, 0])
            before = copy.deepcopy(self.profile)
            adopted = editor.adopt(self.profile, 'nes')
            self.assertEqual(self.profile, before)
            self.assertEqual(adopted['system'], 'nes')
            self.assertAlmostEqual(adopted['objects']['console']['position'][1], 48.93 - 36 + 72)
            self.assertEqual(adopted['objects']['console']['rotation'], [0, -27, 0])
            for name in editor.NAMES:
                node, old = adopted['objects'][name], before['objects'][name]
                if name.startswith('cart'):
                    # NES Game Paks rest 0.5 mm lower than the SNES carts the layout used.
                    self.assertAlmostEqual(node['position'][1], old['position'][1] - 0.5)
                    self.assertEqual([node['position'][0], node['position'][2], node['rotation']],
                                     [old['position'][0], old['position'][2], old['rotation']])
                elif name != 'console':
                    self.assertEqual(node, old)
            self.assertEqual(adopted['camera'], before['camera'])
            self.assertEqual(editor.adopt(self.profile, 'snes'), editor.validate(self.profile))
        finally:
            editor.console_bottom, editor.media_bottom = original, original_media

    def test_partial_expansion_is_rejected(self):
        for count in (9, 10, 11, 13):
            p = copy.deepcopy(self.profile)
            p['objects'] = {name: dict(position=[0, 0, 0], rotation=[0, 0, 0])
                            for name in ['table', 'tv', 'console', 'status'] + [f'cart{i}' for i in range(count)]}
            with self.assertRaises(ValueError):
                editor.validate(p)

    def test_extended_camera_furniture_display_native_roundtrip(self):
        p = self.profile
        p['cameras'] = {key: copy.deepcopy(p['camera']) for key in ('all', 'tv', 'cartridge', 'console', 'inspect')}
        p['cameras']['tv']['position'] = [0, 220, 1200]
        p['transitionSeconds'] = 1.2
        p['browseView'] = 'console'
        p['table'] = dict(model='tv-stand', scale=[1.2, .8, 1.4])
        display = dict(enabled=True, layout='text', textScale=.8, padding=18, background='#102030', foreground='#eeddcc', accent='#123abc', fields={key: key not in ('video', 'hud') for key in FIELDS})
        p['displays'] = dict(tv=display, handheld=dict(display, enabled=False))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'extended.scene'
            path.write_text(editor.native_text(p))
            self.assertEqual(editor.read_profile(path), p)
        self.assertEqual(editor.validate(p)['camera'], self.profile['camera'])

    def test_invalid_extensions_are_rejected(self):
        cases = [dict(table=dict(model='../secret', scale=[1, 1, 1])), dict(table=dict(model='table', scale=[0, 1, 1])),
                 dict(transitionSeconds=float('nan')), dict(browseView='inspect'),
                 dict(cameras={'arbitrary': self.profile['camera']}), dict(cameras={'tv': dict(self.profile['camera'], fov=111)}),
                 dict(displays={}), dict(cameras={'all':dict(self.profile['camera'], fov=50)})]
        for extras in cases:
            with self.subTest(extras=extras), self.assertRaises(ValueError):
                editor.validate(dict(self.profile, **extras))

    def test_handheld_units_pose_and_tv_adoption_preserve_camera(self):
        self.assertEqual(editor.manifest('nds')['consoleUnits'], 3.037594)
        self.assertEqual(editor.manifest('nds')['media']['units'], 2.75)
        for system in ('gb', 'gbc', 'gba', 'nds', 'psp', 'pico8'):
            self.assertIn(system, editor.SYSTEMS)
            manifest = editor.manifest(system)
            for screen in manifest['lcd']:
                self.assertEqual(len(screen), 12)
                self.assertGreater(max(abs(v) for v in screen), 20)  # geometry, not screen UVs
            adopted = editor.adopt(self.profile, system)
            for tv in ('pvm', 'oldtv'):
                output = editor.adopt_tv(adopted, tv)
                self.assertEqual(output['camera'], self.profile['camera'])
                self.assertEqual(output['tv'], tv)
                self.assertEqual(editor.saved_path(system, tv).name, system+'-'+tv+'.json')

    def test_save_endpoint_isolated_history_and_origin_guard(self):
        original_root, original_assets = editor.ROOT, editor.ASSETS
        with tempfile.TemporaryDirectory() as folder:
            editor.ROOT = Path(folder)
            editor.ASSETS = Path(folder) / 'assets'
            editor.ASSETS.mkdir()
            server = editor.ThreadingHTTPServer(('127.0.0.1', 0), editor.Handler)
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            url = 'http://127.0.0.1:' + str(server.server_port)
            profile = dict(self.profile, system='nds', tv='pvm', table=dict(model='wooden-table', scale=[1.5, 1.5, 1.5]))
            def post(value, origin=url):
                request = urllib.request.Request(url+'/api/save', data=json.dumps(value).encode(), headers={'Content-Type':'application/json', 'Origin':origin, 'X-Scene-Token':editor.TOKEN})
                return json.load(urllib.request.urlopen(request))
            try:
                self.assertTrue(post(profile)['saved'])
                saved = editor.saved_path('nds', 'pvm')
                before = saved.read_bytes()
                profile['camera']['fov'] = 42
                self.assertTrue(post(profile)['saved'])
                self.assertEqual(next((editor.ROOT/'scene-layouts/history').iterdir()).read_bytes(), before)
                self.assertEqual(editor.native_path('nds','pvm').read_text(), editor.native_text(profile))
                with self.assertRaises(urllib.error.HTTPError) as failure:
                    post(profile, 'https://other.example')
                self.assertEqual(failure.exception.code, 403)
                self.assertFalse(editor.saved_path('snes').exists())
            finally:
                server.shutdown()
                server.server_close()
                worker.join()
                editor.ROOT, editor.ASSETS = original_root, original_assets

    def test_device_layout_text_imports_with_its_console_and_tv(self):
        profile = dict(copy.deepcopy(self.profile), system='gba', tv='pvm', browseView='cartridge', transitionSeconds=.8,
                       cameras={'all': copy.deepcopy(self.profile['camera']),
                                'console': dict(position=[158.0, 126.5, 792.2], target=[308.0, 133.1, 650.4], fov=40.0)})
        imported = editor.expand_profile(editor.parse_native(editor.native_text(profile), 'gba', 'pvm'))
        self.assertEqual(editor.native_text(imported), editor.native_text(profile))
        self.assertEqual((imported['system'], imported['tv']), ('gba', 'pvm'))
        with self.assertRaises(ValueError):
            editor.parse_native('', 'gba', 'pvm')

    def test_export_saves_each_group_console_resting_on_the_table(self):
        group = editor.GROUPS['handheld']
        bottoms = {s: (editor.console_bottom(s), editor.media_bottom(s)) for s in group}
        saved = dict(root=editor.ROOT, assets=editor.ASSETS, console=editor.console_bottom, media=editor.media_bottom)
        profile = dict(copy.deepcopy(self.profile), system='gba', tv='pvm',
                       cameras={'all': copy.deepcopy(self.profile['camera']),
                                'console': dict(position=[150.0, 120.0, 800.0], target=[300.0, 130.0, 650.0], fov=40.0),
                                'cartridge': dict(position=[190.0, 90.0, 600.0], target=[90.0, 17.5, 490.0], fov=17.0)})
        profile['objects']['console'] = dict(position=[306.0, 115.0, 653.0], rotation=[34.0, -20.0, 0.0])
        profile['objects']['cart0'] = dict(position=[91.0, 17.5, 493.0], rotation=[0.0, 27.0, 0.0])
        try:
            with tempfile.TemporaryDirectory() as folder:
                editor.ROOT, editor.ASSETS = Path(folder), Path(folder) / 'assets'
                editor.ASSETS.mkdir()
                editor.console_bottom = lambda s: bottoms[s][0]
                editor.media_bottom = lambda s: bottoms[s][1]
                plan = editor.export_plan('gba', 'pvm', 'handheld')
                self.assertEqual([p['system'] for p in plan], list(group))
                self.assertEqual([p['system'] for p in plan if p['current']], ['gba'])
                self.assertFalse(any(p['saved'] for p in plan))
                results = editor.export_profile(profile, 'handheld')
                self.assertEqual([r['system'] for r in results], list(group))
                for system in group:
                    out = json.loads(editor.saved_path(system, 'pvm').read_text(encoding='utf-8'))
                    lift, rest = bottoms['gba'][0] - bottoms[system][0], bottoms['gba'][1] - bottoms[system][1]
                    self.assertEqual((out['system'], out['tv']), (system, 'pvm'))
                    self.assertAlmostEqual(out['objects']['console']['position'][1], 115.0 + lift, places=6)
                    self.assertAlmostEqual(out['objects']['cart0']['position'][1], 17.5 + rest, places=6)
                    self.assertAlmostEqual(out['cameras']['console']['target'][1], 130.0 + lift, places=6)
                    self.assertAlmostEqual(out['cameras']['cartridge']['position'][1], 90.0 + rest, places=6)
                    self.assertEqual(out['camera'], editor.validate(profile)['camera'])
                    self.assertEqual(editor.native_path(system, 'pvm').read_text(), editor.native_text(out))
                with self.assertRaises(ValueError):
                    editor.export_plan('gba', 'pvm', 'everything')
                profile['camera']['fov'] = 41.0
                profile['cameras']['all']['fov'] = 41.0
                self.assertTrue(all(r['replaced'] for r in editor.export_profile(profile, 'handheld')))
                self.assertEqual(len(list((editor.ROOT / 'scene-layouts/history').iterdir())), len(group))
                self.assertFalse(editor.saved_path('snes', 'pvm').exists())
        finally:
            editor.ROOT, editor.ASSETS = saved['root'], saved['assets']
            editor.console_bottom, editor.media_bottom = saved['console'], saved['media']

    def test_unchanged_renderer_preserves_authored_json_bytes(self):
        original_root, original_assets = editor.ROOT, editor.ASSETS
        try:
            with tempfile.TemporaryDirectory() as folder:
                editor.ROOT, editor.ASSETS = Path(folder), Path(folder) / 'assets'
                editor.ASSETS.mkdir()
                editor.save_profile(self.profile)
                saved = editor.saved_path('snes')
                saved.write_bytes(saved.read_bytes().replace(b'\n', b'\r\n'))
                before = saved.read_bytes()
                value = copy.deepcopy(self.profile)
                value['camera']['position'][0] += 1e-13
                editor.save_profile(value)
                self.assertEqual(saved.read_bytes(), before)
                self.assertFalse((editor.ROOT / 'scene-layouts/history').exists())
        finally:
            editor.ROOT, editor.ASSETS = original_root, original_assets


if __name__ == '__main__':
    unittest.main()
