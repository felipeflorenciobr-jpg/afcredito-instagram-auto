"""Falhas de publicação não podem causar uma segunda tentativa automática."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import campanha_novembro as campaign

class PublicationSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.item={'date':'2026-11-04','slot':'10','type':'FEED','caption':'Teste','media_sha256':'a'*64}
        (self.root/'nov2026_2026-11-04_10.jpg').write_bytes(b'test')
        self.patches=[patch.object(campaign,'MEDIA',self.root),patch.object(campaign,'LEDGER',self.root/'ledger.json'),patch.object(campaign,'posts',return_value=[self.item])]
        for p in self.patches:p.start()
        self.addCleanup(self.tmp.cleanup)
        for p in self.patches:self.addCleanup(p.stop)

    def test_disabled_publication_never_calls_meta(self):
        with patch.dict(os.environ,{'PUBLISH_ENABLED':'false','CAMPANHA_NOVEMBRO_APPROVED':'true'}),patch.object(campaign.bot,'verify') as verify:
            campaign.publish('2026-11-04','10')
            verify.assert_not_called()

    def test_uncertain_publication_is_persisted_and_not_repeated(self):
        response=MagicMock()
        response.__enter__.return_value.status=200
        response.__enter__.return_value.headers={'Content-Type':'image/jpeg'}
        def meta(path,method='GET',data=None):
            if path.endswith('/media'):return {'id':'container1'}
            if path.endswith('/media_publish'):raise TimeoutError('Resposta perdida após envio')
            return {'status_code':'FINISHED'}
        with patch.dict(os.environ,{'PUBLISH_ENABLED':'true','CAMPANHA_NOVEMBRO_APPROVED':'true'}),patch.object(campaign.bot,'verify',return_value='correct_account'),patch.object(campaign.bot,'api',side_effect=meta) as api,patch.object(campaign.urllib.request,'urlopen',return_value=response):
            with self.assertRaises(TimeoutError):campaign.publish('2026-11-04','10')
            ledger=json.loads((self.root/'ledger.json').read_text())
            self.assertEqual(ledger['nov2026_2026-11-04_10']['status'],'publish_attempted')
            count=api.call_count
            campaign.publish('2026-11-04','10')
            self.assertEqual(api.call_count,count)

    def test_dry_run_never_connects_to_meta(self):
        with patch.object(campaign.bot,'verify') as verify:
            campaign.publish('2026-11-04','10',dry_run=True)
            verify.assert_not_called()

class VisualDiversityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        (self.root/'campanhas').mkdir()
        for name in ('first.jpg','alias.jpg'):
            (self.root/'campanhas'/name).write_bytes(b'same master image')
        self.addCleanup(self.tmp.cleanup)

    def test_renaming_an_image_does_not_hide_a_repeated_feed(self):
        from premium_campaign import validate_diversity
        items=[{'date':'2026-11-04','type':'FEED','artwork':'first.jpg'},
               {'date':'2026-11-20','type':'FEED','artwork':'alias.jpg'}]
        with self.assertRaisesRegex(ValueError,'Arte repetida'):validate_diversity(items,self.root)

    def test_feed_and_story_cannot_reuse_an_image_in_the_same_week(self):
        from premium_campaign import validate_diversity
        items=[{'date':'2026-11-04','type':'FEED','artwork':'first.jpg'},
               {'date':'2026-11-10','type':'STORY','artwork':'alias.jpg'}]
        with self.assertRaisesRegex(ValueError,'12 dias'):validate_diversity(items,self.root)

    def test_reuse_in_the_other_format_after_twelve_days_is_allowed(self):
        from premium_campaign import validate_diversity
        items=[{'date':'2026-11-04','type':'FEED','artwork':'first.jpg'},
               {'date':'2026-11-16','type':'STORY','artwork':'alias.jpg'}]
        validate_diversity(items,self.root)

if __name__=='__main__':unittest.main()
