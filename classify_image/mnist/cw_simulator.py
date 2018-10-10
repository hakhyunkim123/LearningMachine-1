from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import numpy as np
import tensorflow as tf
from tensorflow.python.platform import flags

import logging
import os
from cleverhans.attacks import CarliniWagnerL2
from cleverhans.utils import set_log_level
from cleverhans_tutorials.tutorial_models import ModelBasicCNN

from mnist_handle import get_mnist_data
from mnist_handle import get_mnist_idx

FLAGS = flags.FLAGS

abs_path = os.path.abspath(os.path.join(os.path.dirname(__file__),".."))
SAVE_PATH = os.path.join(abs_path, 'output/testtest.png')

def mnist_cw_attack(sample, target, model, sess, targeted=True, attack_iterations=10) :
    cw = CarliniWagnerL2(model, back='tf', sess=sess)

    if targeted:
        adv_input = sample
        adv_ys = target
        yname = "y_target"
    else:
        adv_input = sample
        adv_ys = None
        yname = "y"
    cw_params = {'binary_search_steps': 1,
                yname: adv_ys,
                'max_iterations': attack_iterations,
                'learning_rate': 0.1,
                'batch_size': 1,
                'initial_const': 10}

    adv = cw.generate_np(adv_input, **cw_params)
    return adv

def mnist_tutorial_cw(nb_classes=10, attack_iterations=100, targeted=True):

    # MNIST-specific dimensions
    img_rows = 28
    img_cols = 28
    channels = 1

    # Set TF random seed to improve reproducibility
    tf.set_random_seed(1234)

    # Create TF session
    sess = tf.Session()
    print("Created TensorFlow session.")

    set_log_level(logging.DEBUG)

    # Get MNIST test data
    x_test, y_test = get_mnist_data()

    # Define input TF placeholder
    x = tf.placeholder(tf.float32, shape=(None, img_rows, img_cols, channels))
    y = tf.placeholder(tf.float32, shape=(None, nb_classes))

    # Define TF model graph
    model = ModelBasicCNN('model1', 10, 64)
    preds = model.get_logits(x)
    print("Defined TensorFlow model graph.")

    ############ Select sample and target class ############
    sample_class = int(input('input sample class(0-9): '))
    target_class = int(input('input target class(0-9): '))

    if sample_class<0 or sample_class>9 or target_class<0 or target_class>9 :
        print('input is wrong')
        return

    sample_idx = get_mnist_idx(y_test, sample_class)
    target_idx = get_mnist_idx(y_test, target_class)

    sample = x_test[sample_idx:sample_idx+1]
    target = y_test[target_idx:target_idx+1]
    ############ ############################## ############

    ##################################
    #          Load Model            #
    ##################################
    saver = tf.train.Saver()
    init_op = tf.global_variables_initializer()
    with tf.Session() as sess:
        sess.run(init_op)
        saver = tf.train.import_meta_graph('./model/mnist_model.ckpt.meta')
        current_dir = os.getcwd()
        path = os.path.join(current_dir, 'model/mnist_model.ckpt')
        saver.restore(sess, path)
        
        # Instantiate a CW attack object
        adv = mnist_cw_attack(sample, target, model, sess)

        # Prediction
        feed_dict = {x: adv}
        probabilities = sess.run(preds, feed_dict)
        print(probabilities)

        #Save adversial image
        two_d_img = (np.reshape(adv, (28, 28)) * 255).astype(np.uint8)
        from PIL import Image
        save_image = Image.fromarray(two_d_img)
        save_image = save_image.convert('RGB')
        save_image.save(SAVE_PATH)

        # Close TF session
        sess.close()
    return


def main(argv=None):
    mnist_tutorial_cw(nb_classes=FLAGS.nb_classes,
                      attack_iterations=FLAGS.attack_iterations,
                      targeted=FLAGS.targeted)


if __name__ == '__main__':
    flags.DEFINE_integer('nb_classes', 10, 'Number of output classes')
    flags.DEFINE_integer('attack_iterations', 100,
                         'Number of iterations to run attack; 1000 is good')
    flags.DEFINE_boolean('targeted', True,
                         'Run the tutorial in targeted mode?')

    tf.app.run()
