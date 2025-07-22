import tensorflow as tf
import numpy as np
import cv2

import tensorflow as tf
import numpy as np
import cv2

import tensorflow as tf
import numpy as np

import tensorflow as tf
import numpy as np

from tensorflow.keras.models import clone_model
from tensorflow.keras import Input

def compute_gradcam(model, img_array, class_index=1, last_conv_layer_name="conv2d_3"):
    # 🧠 Sanity check
    print("📋 Outer model summary:")
    model.summary()

    try:
        inner_seq = model.get_layer("sequential")
    except ValueError as e:
        raise ValueError("Could not find 'sequential' layer inside the model.") from e

    print("\n📋 Inner Sequential model summary:")
    inner_seq.summary()

    if not isinstance(inner_seq, tf.keras.Sequential):
        raise ValueError("Expected inner model to be Sequential.")

    # ⚙️ Rebuild model using inner_seq layers
    input_tensor = tf.keras.Input(shape=(224, 224, 3))
    x = input_tensor
    target_layer_output = None

    for layer in inner_seq.layers:
        x = layer(x)
        if layer.name == last_conv_layer_name:
            target_layer_output = x

    if target_layer_output is None:
        raise ValueError(f"Layer '{last_conv_layer_name}' not found in Sequential.")

    grad_model = tf.keras.Model(inputs=input_tensor, outputs=[target_layer_output, x])

    # 🚀 Grad-CAM core
    img_tensor = tf.convert_to_tensor(img_array, dtype=tf.float32)
    with tf.GradientTape() as tape:
        tape.watch(img_tensor)
        conv_outputs, predictions = grad_model(img_tensor)
        print("✅ Predictions shape:", predictions.shape)
        print("✅ Class index:", class_index)
        loss = predictions[:, class_index]

    grads = tape.gradient(loss, conv_outputs)
    pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))
    conv_outputs = conv_outputs[0]
    heatmap = tf.reduce_sum(conv_outputs * pooled_grads, axis=-1)

    heatmap = tf.maximum(heatmap, 0) / tf.reduce_max(heatmap + 1e-6)
    heatmap = tf.image.resize(heatmap[..., tf.newaxis], (224, 224))
    heatmap = tf.cast(heatmap * 255, tf.uint8).numpy().squeeze()
    return heatmap


def overlay_gradcam(heatmap, image_array, alpha=0.4):
    heatmap = cv2.resize(heatmap, (image_array.shape[2], image_array.shape[1]))
    heatmap = np.uint8(255 * heatmap)
    jet = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)
    image = image_array[0].astype("uint8")
    superimposed_img = cv2.addWeighted(image, 1 - alpha, jet, alpha, 0)
    return superimposed_img
