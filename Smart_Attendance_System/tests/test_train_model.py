import os

from train_model import _select_training_images


def test_training_images_span_oldest_to_newest_capture(tmp_path):
    images = []
    for index in range(120):
        image = tmp_path / f"capture-{index:03}.jpg"
        image.touch()
        os.utime(image, (index, index))
        images.append(image)

    selected = _select_training_images(images)

    assert len(selected) == 60
    assert selected[0] == images[0]
    assert selected[-1] == images[-1]
    assert len(set(selected)) == len(selected)