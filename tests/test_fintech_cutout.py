from src.fintech_cutout import InfraiClient, ListingImage, prepare_listing


class FakeClient(InfraiClient):
    def __init__(self):
        pass

    def upload(self, image):
        return {"image_id": "img_123"}

    def remove_background(self, image_id, image_format):
        assert image_id == "img_123"
        assert image_format == "png"
        return {"id": "cutout_456", "format": image_format}


def test_listing_emits_auditable_background_decision():
    result, notice = prepare_listing("listing-7", ListingImage("card.jpg", b"x"), FakeClient())
    assert result["listing_id"] == "listing-7"
    assert result["image"]["id"] == "cutout_456"
    assert notice.action == "background_removed"
    assert result["audit"]["image_id"] == "img_123"
