"""按固定版本OpenVLA LIBERO评测实现的CPU图像处理。输入已经旋转180度。"""
import numpy as np


def preprocess_image(rotated_rgb):
    import tensorflow as tf
    pixels=np.asarray(rotated_rgb)
    if pixels.ndim!=3 or pixels.shape[2]!=3 or pixels.dtype!=np.uint8:
        raise ValueError('需要已旋转的uint8 RGB相机帧')
    with tf.device('/CPU:0'):
        image=tf.image.encode_jpeg(pixels)
        image=tf.io.decode_image(image,expand_animations=False,dtype=tf.uint8)
        image=tf.image.resize(image,(224,224),method='lanczos3',antialias=True)
        image=tf.cast(tf.clip_by_value(tf.round(image),0,255),tf.uint8)
        image=tf.image.convert_image_dtype(image,tf.float32)
        size=tf.sqrt(tf.constant(.9,tf.float32))
        offset=(1-size)/2
        box=tf.stack([offset,offset,offset+size,offset+size])[None,:]
        image=tf.image.crop_and_resize(image[None,...],box,[0],(224,224))[0]
        image=tf.image.convert_image_dtype(tf.clip_by_value(image,0,1),tf.uint8,saturate=True)
        return image.numpy()
