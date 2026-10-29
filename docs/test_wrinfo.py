import contextlib
import gzip
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import pandas as pd
import requests

from wrinfo import (
    SCRYFALL_HEADERS,
    build_table_data,
    card_metadata,
    find_card_metadata,
    fetch_card_individually,
    fetch_scryfall_bulk_data,
    process_results_folder,
    read_bulk_cards,
)


class BulkDataTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        directory_patch = patch("wrinfo.SCRYFALL_DATA_DIR", self.directory)
        directory_patch.start()
        self.addCleanup(directory_patch.stop)
        cache_patch = patch("wrinfo._SCRYFALL_CACHE", None)
        cache_patch.start()
        self.addCleanup(cache_patch.stop)
        self.card = {
            "object": "card", "name": "Time Walk",
            "type_line": "Sorcery", "rarity": "mythic",
            "image_uris": {"normal": "card.jpg", "art_crop": "art.jpg"},
        }

    def test_local_archive_uses_newest_and_caches_without_network(self):
        for date, name in [("20261028", "Old Card"), ("20261029", "Time Walk")]:
            card = dict(self.card, name=name)
            with gzip.open(self.directory / f"oracle-cards-{date}.jsonl.gz", "wt") as stream:
                stream.write(json.dumps(card) + "\n")
        with patch("wrinfo.requests.get") as get:
            with contextlib.chdir(self.directory):
                lookup = fetch_scryfall_bulk_data()
            self.assertEqual(lookup["Time Walk"]["image"], "card.jpg")
            self.assertEqual(lookup["Time Walk"]["types"], ["Sorcery"])
            self.assertEqual(lookup["Time Walk"]["rarity"], "mythic")
            self.assertNotIn("Old Card", lookup)
            self.assertIs(fetch_scryfall_bulk_data(), lookup)
            get.assert_not_called()

    def test_remote_current_format_and_legacy_array(self):
        for field, content in [
            ("jsonl_download_uri", gzip.compress((json.dumps(self.card) + "\n").encode())),
            ("download_uri", json.dumps([self.card]).encode()),
        ]:
            with self.subTest(field=field), patch("wrinfo._SCRYFALL_CACHE", None):
                metadata = MagicMock()
                metadata.json.return_value = {field: "https://example.test/cards"}
                response = MagicMock()
                response.content = content
                response.__enter__.return_value = response
                with patch("wrinfo.requests.get", side_effect=[metadata, response]) as get:
                    self.assertEqual(fetch_scryfall_bulk_data()["Time Walk"]["art"], "art.jpg")
                    metadata.raise_for_status.assert_called_once()
                    response.raise_for_status.assert_called_once()
                    for call in get.call_args_list:
                        self.assertEqual(call.kwargs["headers"], SCRYFALL_HEADERS)
                        self.assertGreater(call.kwargs["timeout"], 0)

    def test_bulk_errors_do_not_become_empty_success(self):
        metadata = MagicMock()
        metadata.raise_for_status.side_effect = requests.HTTPError("403 Forbidden")
        with patch("wrinfo.requests.get", return_value=metadata):
            with self.assertRaises(requests.HTTPError):
                fetch_scryfall_bulk_data()
        (self.directory / "oracle-cards-20261029.jsonl.gz").write_bytes(b"corrupt")
        with patch("wrinfo.requests.get") as get:
            with self.assertRaises(OSError):
                fetch_scryfall_bulk_data()
            get.assert_not_called()

    def test_json_lines_and_pretty_printed_legacy_arrays(self):
        for text in [
            "\n" + json.dumps(self.card) + "\n",
            json.dumps([self.card], indent=2),
        ]:
            self.assertEqual(list(read_bulk_cards(io.StringIO(text))), [self.card])

    def test_individual_requests_include_required_headers(self):
        response = MagicMock(status_code=200)
        response.json.return_value = self.card
        lookup = {}
        with patch("wrinfo.requests.get", return_value=response) as get:
            self.assertEqual(fetch_card_individually("Time Walk", lookup)["image"], "card.jpg")
            self.assertEqual(get.call_args.kwargs["headers"], SCRYFALL_HEADERS)
            response.raise_for_status.assert_called_once()

    def test_face_names_resolve_without_individual_requests(self):
        card = {
            "name": "Front // Back",
            "rarity": "rare",
            "card_faces": [
                {"name": "Front", "type_line": "Artifact Creature — Elf",
                 "image_uris": {"normal": "front.jpg"}},
                {"name": "Back", "printed_name": "Translated Back",
                 "type_line": "Land",
                 "image_uris": {"normal": "back.jpg"}},
            ],
        }
        with gzip.open(self.directory / "oracle-cards-20261029.jsonl.gz", "wt") as stream:
            stream.write(json.dumps(card) + "\n")
        with patch("wrinfo.requests.get") as get:
            lookup = fetch_scryfall_bulk_data()
            self.assertEqual(lookup["Front"]["image"], "front.jpg")
            self.assertEqual(lookup["Back"]["image"], "back.jpg")
            self.assertEqual(lookup["Translated Back"]["image"], "back.jpg")
            self.assertEqual(lookup["Front"]["types"], ["Creature", "Artifact", "Land"])
            self.assertEqual(lookup["Back"]["rarity"], "rare")
            get.assert_not_called()

    def test_metadata_ignores_subtypes_and_handles_missing_cards(self):
        self.assertEqual(
            card_metadata({"type_line": "Kindred Enchantment — Creature", "rarity": "uncommon"}),
            {"types": ["Enchantment", "Kindred"], "rarity": "uncommon"},
        )
        self.assertEqual(
            card_metadata({"type_line": "Creature — Elf // Land", "rarity": "rare"}),
            {"types": ["Creature", "Land"], "rarity": "rare"},
        )
        self.assertEqual(find_card_metadata("Missing", {}), {"types": [], "rarity": None})
        self.assertEqual(
            find_card_metadata("Name", {"Náme": {"types": ["Sorcery"], "rarity": "common"}}),
            {"types": ["Sorcery"], "rarity": "common"},
        )

    def test_art_series_cannot_override_playable_card_metadata(self):
        art = {
            "name": "Time Walk // Time Walk", "layout": "art_series",
            "type_line": "Card // Card", "rarity": "common",
            "highres_image": True,
            "card_faces": [{"name": "Time Walk", "image_uris": {"normal": "art.jpg"}}],
        }
        with gzip.open(self.directory / "oracle-cards-20261029.jsonl.gz", "wt") as stream:
            for card in [art, self.card, art]:
                stream.write(json.dumps(card) + "\n")
        lookup = fetch_scryfall_bulk_data()
        self.assertEqual(lookup["Time Walk"]["types"], ["Sorcery"])
        self.assertEqual(lookup["Time Walk"]["rarity"], "mythic")

class TableDataTests(unittest.TestCase):
    def test_weights_and_feature_specific_counts_are_preserved(self):
        cards = pd.DataFrame([
            {"feature": "Card A", "odds_multiplier": 1.25, "count": 100},
            {"feature": "Card B", "odds_multiplier": 0.8, "count": 50},
        ])
        repeats = pd.DataFrame([
            {"feature": "Card A (repeat)", "odds_multiplier": 0.9, "count": 12},
            {"feature": "Card B (repeat)", "odds_multiplier": 1.0, "count": 0},
        ])
        pairs = pd.DataFrame([
            {"feature": "Card A × Card B", "odds_multiplier": 0.7, "count": 8},
            {"feature": "Card B × Card A", "odds_multiplier": 0.7, "count": 8},
            {"feature": "Card A × Card A", "odds_multiplier": 1.5, "count": 12},
            {"feature": "Card A × Card C", "odds_multiplier": 1.0, "count": 3},
        ])

        tables = build_table_data(cards, repeats, pairs)

        self.assertEqual(tables["alone"], [
            {"card": "Card A", "weight": 1.25, "games": 100},
            {"card": "Card B", "weight": 0.8, "games": 50},
        ])
        self.assertEqual(tables["self"], [
            {"card": "Card A", "weight": 0.9, "games": 12},
            {"card": "Card B", "weight": 1.0, "games": 0},
        ])
        self.assertEqual(tables["pairs"], [
            {"source": "Card A", "target": "Card B", "weight": 0.7, "games": 8},
            {"source": "Card A", "target": "Card C", "weight": 1.0, "games": 3},
        ])
        self.assertEqual(list(cards.columns), ["feature", "odds_multiplier", "count"])
        self.assertEqual(repeats.iloc[0]["feature"], "Card A (repeat)")

    def test_empty_inputs_produce_empty_tables(self):
        empty = pd.DataFrame(columns=["feature", "odds_multiplier", "count"])
        self.assertEqual(
            build_table_data(empty, empty, empty),
            {"alone": [], "self": [], "pairs": []},
        )

    def test_export_keeps_all_table_pairs_without_changing_graph_filter(self):
        cards = pd.DataFrame([
            {"feature": "Card A", "odds_multiplier": 1.2, "count": 100},
            {"feature": "Card B", "odds_multiplier": 0.9, "count": 50},
            {"feature": "Card C", "odds_multiplier": 1.1, "count": 75},
        ])
        repeats = cards.copy()
        repeats["feature"] += " (repeat)"
        pairs = pd.DataFrame([
            {"feature": "Card A × Card B", "odds_multiplier": 0.7, "count": 8},
            {"feature": "Card A × Card C", "odds_multiplier": 1.2, "count": 10},
            {"feature": "Card B × Card C", "odds_multiplier": 1.5, "count": 20},
        ])
        images = {
            name: {"image": "card.jpg", "art": "art.jpg", "types": ["Creature"], "rarity": "rare"}
            for name in cards["feature"]
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "example"
            source.mkdir()
            for suffix, frame in [
                ("card_rankings", cards),
                ("squared_terms", repeats),
                ("pair_synergies", pairs),
            ]:
                frame.to_csv(source / f"drawn_without_basics_{suffix}.csv", index=False)
            with contextlib.chdir(root), contextlib.redirect_stdout(io.StringIO()):
                with patch("wrinfo.fetch_scryfall_bulk_data", return_value=images):
                    self.assertTrue(process_results_folder(source))
            data = json.loads((root / "data/example/data.json").read_text())

        self.assertEqual(len(data["nodes"]), 3)
        self.assertTrue(all(node["types"] == ["Creature"] for node in data["nodes"]))
        self.assertTrue(all(node["rarity"] == "rare" for node in data["nodes"]))
        self.assertEqual([link["weight"] for link in data["links"]], [1.2, 1.5])
        self.assertEqual(data["tables"], build_table_data(cards, repeats, pairs))


if __name__ == "__main__":
    unittest.main()
