from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os

import numpy as np
from six.moves import xrange
import tensorflow as tf
from tensorflow.python.platform import flags
import logging

import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from cleverhans.attacks import SaliencyMapMethod
from cleverhans.attacks import FastGradientMethod
from cleverhans.attacks import CarliniWagnerL2
from cleverhans.attacks import DeepFool
from cleverhans.utils import other_classes, set_log_level
from cleverhans.attacks_tf import imgs_stamp_tf 

sys.path.append(os.path.dirname(__file__))
from mymodel import ModelBasicCNN
from classify_image.mnist.mnist_handle import get_mnist_data
from classify_image.mnist.mnist_handle import get_mnist_idx

abs_path = os.path.dirname(__file__)
SAVE_PATH = os.path.join(abs_path, 'output/testtest.png')
SAVE_GIF_PATH = os.path.join(abs_path, 'output/testtest.gif')
INPUT_PATH = os.path.join(abs_path, 'dataset/images/testtest.png')

# MNIST-specific dimensions
img_rows = 28
img_cols = 28
channels = 1

def mnist_jsma_attack(sample, target, model, sess) :
    jsma = SaliencyMapMethod(model, back='tf', sess=sess)
    jsma_params = {'theta': 1., 'gamma': 3,
            'clip_min': 0., 'clip_max': 1.,
            'y_target': None}
    jsma_params['y_target'] = target

    adv = jsma.generate_np(sample, **jsma_params)
    return adv

def mnist_fgsm_attack(sample, target, model, sess) :
    imgs_stamp_tf.append(sample)

    fgsm_params = {
        'eps': 0.1,
        'clip_min': 0.,
        'clip_max': 1.,
        'y_target': target
    }
    fgsm = FastGradientMethod(model, sess=sess)
    adv = fgsm.generate_np(sample, **fgsm_params)
    imgs_stamp_tf.append(adv)
    for i in range(2):
        adv = fgsm.generate_np(adv, **fgsm_params)
        imgs_stamp_tf.append(adv)
    return adv

def mnist_cw_attack(sample, target, model, sess, targeted=True, attack_iterations=100) :
    cw = CarliniWagnerL2(model, back='tf', sess=sess)

    if targeted:
        adv_input = sample
        adv_ys = target
        yname = "y_target"
    else:
        adv_input = sample
        adv_ys = None
        yname = "y"
    cw_params = {'binary_search_steps': 1, 'abort_early': False,
                yname: adv_ys,
                'confidence' : 1,
                'max_iterations': attack_iterations,
                'learning_rate': 0.1,
                'clip_min': 0.,
                'clip_max': 1.,
                'initial_const': 10}

    adv = cw.generate_np(adv_input, **cw_params)
    return adv

def mnist_deepfool_attack(sample, target, model, sess, targeted=True, attack_iterations=100) :
    print('deepfool attack start')
    deepfool = DeepFool(model, sess=sess)
    deepfool_params = { 'over_shoot': 0.02, 'clip_min': 0.,
                'clip_max': 1., 'max_iter': 300, 'nb_candidate': 2,}
    adv_x = deepfool.generate_np(sample, **deepfool_params)
    return adv_x

def mnist_attack_func(sample_class, target_class, mnist_algorithm):
    # Get MNIST test data
    x_test, y_test = get_mnist_data()
    # Define input TF placeholder
    x = tf.placeholder(tf.float32, shape=(None, img_rows, img_cols, channels))
    y = tf.placeholder(tf.float32, shape=(None, 10))
    # Define TF model graph
    model = ModelBasicCNN('model1', 10, 64)
    preds = model.get_logits(x)
    print("Defined TensorFlow model graph.")

    if sample_class<0 or sample_class>9 or target_class<0 or target_class>9 :
        print('input is wrong')
        return
    sample_idx = get_mnist_idx(y_test, sample_class)
    target_idx = get_mnist_idx(y_test, target_class)

    sample = x_test[sample_idx:sample_idx+1]
    # save the adverisal image #
    two_d_img = (np.reshape(sample, (28, 28)) * 255).astype(np.uint8)
    from PIL import Image
    save_image = Image.fromarray(two_d_img)
    save_image = save_image.convert('RGB')
    save_image.save(INPUT_PATH)

    ############ ############################## ############

    ##################################
    #          Load Model            #
    ##################################
    saver = tf.train.Saver()
    init_op = tf.global_variables_initializer()
    with tf.Session() as sess:
        sess.run(init_op)
        saver = tf.train.import_meta_graph(os.path.join(abs_path,'model/mnist_model.ckpt.meta'))
        path = os.path.join(abs_path, 'model/mnist_model.ckpt')
        saver.restore(sess, path)

        def softmax(x):
            e_x = np.exp(x - np.max(x))
            return e_x / e_x.sum()

        feed_dict = {x: sample}
        sample_probabilities = sess.run(preds, feed_dict)

        sample_result = softmax(sample_probabilities)

        target = y_test[target_idx:target_idx+1]

        print(mnist_algorithm, 'attack start')

        import time
        start_time = time.time() 
        if mnist_algorithm == 'JSMA':
            adv_x = mnist_jsma_attack(sample, target, model, sess)
        elif mnist_algorithm == 'FGSM':
            adv_x = mnist_fgsm_attack(sample, target, model, sess)
        elif mnist_algorithm == 'CWL2':
            adv_x = mnist_cw_attack(sample, target, model, sess)
        elif mnist_algorithm == 'DeepFool':
            adv_x = mnist_deepfool_attack(sample, target, model, sess)
        attack_time = time.time() - start_time

        print('attack is ended')

        # Get array of output
        feed_dict = {x: adv_x}
        probabilities = sess.run(preds, feed_dict)

        adver_result = softmax(probabilities)

    # save the adverisal image #
    two_d_img = (np.reshape(adv_x, (28, 28)) * 255).astype(np.uint8)
    from PIL import Image
    save_image = Image.fromarray(two_d_img)
    save_image = save_image.convert('RGB')
    save_image.save(SAVE_PATH)


    sv_imgs = []
    for i in range(len(imgs_stamp_tf)):
        two_d_img = (np.reshape(imgs_stamp_tf[i], (28, 28)) * 255).astype(np.uint8)
        save_image = Image.fromarray(two_d_img)
        save_image = save_image.convert('RGB')
        sv_imgs.append(save_image)

    sv_imgs[0].save(SAVE_GIF_PATH,
               save_all=True,
               append_images=sv_imgs[1:],
               duration=40,
               loop=0)
    imgs_stamp_tf.clear()
    
    sess.close()
    return sample_result, adver_result, attack_time
