# -*- coding: utf8 -*-
import os
import sys
import json
import argparse

from collections import OrderedDict

import keras
import keras.backend as K
from keras.models import Sequential, Model

from utils import *
import inputs
import metrics
from losses import *

def load_model(config):
    """Loads a model

    # Arguments
        config: Configuration dictionary.

    # Returns
        When model type is 'JSON',returns a Keras model instance.
        When model type is 'PY',create the object of corresponding model,
        returns the model after calling the 'build()' function
    """

    global_conf = config["global"]
    model_type = global_conf['model_type']
    if model_type == 'JSON':
        mo = Model.from_config(config['model'])
    elif model_type == 'PY':
        model_config = config['model']
        model_config.update(config['inputs']['share'])
        sys.path.insert(0, model_config['model_path'])

        model = import_object(model_config['model_py'], model_config)
        mo = model.build()
    return mo


def train(config):
    """Train a model loaded via 'load_model'

    # Arguments
        config: Configuration dictionary.
    """
    # read basic config
    global_conf = config["global"]
    optimizer = global_conf['optimizer']
    weights_file = global_conf['weights_file']
    num_batch = global_conf['num_batch']

    # read input config
    input_conf = config['inputs']
    share_input_conf = input_conf['share']


    # collect embedding 
    if 'embed_path' in share_input_conf:
        embed_dict = read_embedding(filename=share_input_conf['embed_path'])
        _PAD_ = share_input_conf['fill_word']
        embed_dict[_PAD_] = np.zeros((share_input_conf['embed_size'], ), dtype=np.float32)
        embed = np.float32(np.random.uniform(-0.2, 0.2, [share_input_conf['vocab_size'], share_input_conf['embed_size']]))
        share_input_conf['embed'] = convert_embed_2_numpy(embed_dict, embed = embed)
    else:
        embed = np.float32(np.random.uniform(-0.2, 0.2, [share_input_conf['vocab_size'], share_input_conf['embed_size']]))
        share_input_conf['embed'] = embed
    print '[Embedding] Embedding Load Done.'

    # list all input tags and construct tags config
    input_train_conf = OrderedDict()
    input_eval_conf = OrderedDict()
    for tag in input_conf.keys():
        if 'phase' not in input_conf[tag]:
            continue
        if input_conf[tag]['phase'] == 'TRAIN':
            input_train_conf[tag] = {}
            input_train_conf[tag].update(share_input_conf)
            input_train_conf[tag].update(input_conf[tag])
        elif input_conf[tag]['phase'] == 'EVAL':
            input_eval_conf[tag] = {}
            input_eval_conf[tag].update(share_input_conf)
            input_eval_conf[tag].update(input_conf[tag])
    print '[Input] Process Input Tags. %s in TRAIN, %s in EVAL.' % (input_train_conf.keys(), input_eval_conf.keys())

    # collect dataset identification
    dataset = {}
    for tag in input_conf:
        if tag != 'share' and input_conf[tag]['phase'] == 'PREDICT':
            continue
        if 'text1_corpus' in input_conf[tag]:
            datapath = input_conf[tag]['text1_corpus']
            if datapath not in dataset:
                dataset[datapath], _ = read_data(datapath)
        if 'text2_corpus' in input_conf[tag]:
            datapath = input_conf[tag]['text2_corpus']
            if datapath not in dataset:
                dataset[datapath], _ = read_data(datapath)
    print '[Dataset] %s Dataset Load Done.' % len(dataset)

    # initial data generator
    train_gen = OrderedDict()
    eval_gen = OrderedDict()


    for tag, conf in input_train_conf.items():
        print conf
        conf['data1'] = dataset[conf['text1_corpus']]
        conf['data2'] = dataset[conf['text2_corpus']]
        #get the object of generator
        generator = inputs.get(conf['input_type'])
        #init the generator
        train_gen[tag] = generator( config = conf )

    for tag, conf in input_eval_conf.items():
        print conf
        conf['data1'] = dataset[conf['text1_corpus']]
        conf['data2'] = dataset[conf['text2_corpus']]
        generator = inputs.get(conf['input_type'])
        eval_gen[tag] = generator( config = conf )

    ######### Load Model #########
    ######### Load Model #########
    model = load_model(config)

    loss = []
    for lobj in config['losses']:
      loss.append(rank_losses.get(lobj))
    eval_metrics = OrderedDict()
    for mobj in config['metrics']:
        mobj = mobj.lower()
        if '@' in mobj:
            mt_key, mt_val = mobj.split('@', 1)
            eval_metrics[mobj] = metrics.get(mt_key)(int(mt_val))
        else:
            eval_metrics[mobj] = metrics.get(mobj)
    model.compile(optimizer=optimizer, loss=loss)
    print '[Model] Model Compile Done.'

    for i_e in range(global_conf['num_epochs']):
        print '[Train] @ %s epoch.' % i_e
        for tag, generator in train_gen.items():
            genfun = generator.get_batch_generator()
            print '[Train] @ %s' % tag
            model.fit_generator(
                    genfun,
                    steps_per_epoch = num_batch,
                    epochs = 1,
                    verbose = 1
                ) #callbacks=[eval_map])
        
        for tag, generator in eval_gen.items():
            genfun = generator.get_batch_generator()
            print '[Eval] @ %s ' % tag,
            res = dict([[k,0.] for k in eval_metrics.keys()])
            num_valid = 0
            for input_data, y_true in genfun:
                y_pred = model.predict(input_data, batch_size=len(y_true))
                for k, eval_func in eval_metrics.items():
                    res[k] += eval_func(y_true = y_true, y_pred = y_pred)
                num_valid += 1
            generator.reset()
            print 'epoch: %d,' %( i_e ), '  '.join(['%s:%f'%(k,v/num_valid) for k, v in res.items()])
            sys.stdout.flush()

    model.save_weights(weights_file)

def predict(config):
    ######## Read input config ########

    input_conf = config['inputs']
    share_input_conf = input_conf['share']

    # collect embedding 
    if 'embed_path' in share_input_conf:
        embed_dict = read_embedding(filename=share_input_conf['embed_path'])
        _PAD_ = share_input_conf['fill_word']
        embed_dict[_PAD_] = np.zeros((share_input_conf['embed_size'], ), dtype=np.float32)
        embed = np.float32(np.random.uniform(-0.02, 0.02, [share_input_conf['vocab_size'], share_input_conf['embed_size']]))
        share_input_conf['embed'] = convert_embed_2_numpy(embed_dict, embed = embed)
    else:
        embed = np.float32(np.random.uniform(-0.2, 0.2, [share_input_conf['vocab_size'], share_input_conf['embed_size']]))
        share_input_conf['embed'] = embed
    print '[Embedding] Embedding Load Done.'

    # list all input tags and construct tags config
    input_predict_conf = OrderedDict()
    for tag in input_conf.keys():
        if 'phase' not in input_conf[tag]:
            continue
        if input_conf[tag]['phase'] == 'PREDICT':
            input_predict_conf[tag] = {}
            input_predict_conf[tag].update(share_input_conf)
            input_predict_conf[tag].update(input_conf[tag])
    print '[Input] Process Input Tags. %s in PREDICT.' % (input_predict_conf.keys())

    # collect dataset identification
    dataset = {}
    for tag in input_conf:
        if tag == 'share' or input_conf[tag]['phase'] == 'PREDICT':
            if 'text1_corpus' in input_conf[tag]:
                datapath = input_conf[tag]['text1_corpus']
                if datapath not in dataset:
                    dataset[datapath], _ = read_data(datapath)
            if 'text2_corpus' in input_conf[tag]:
                datapath = input_conf[tag]['text2_corpus']
                if datapath not in dataset:
                    dataset[datapath], _ = read_data(datapath)
    print '[Dataset] %s Dataset Load Done.' % len(dataset)

    # initial data generator
    predict_gen = OrderedDict()

    for tag, conf in input_predict_conf.items():
        print conf
        conf['data1'] = dataset[conf['text1_corpus']]
        conf['data2'] = dataset[conf['text2_corpus']]
        generator = inputs.get(conf['input_type'])
        predict_gen[tag] = generator( 
                                    #data1 = dataset[conf['text1_corpus']],
                                    #data2 = dataset[conf['text2_corpus']],
                                     config = conf )  

    ######## Read output config ########
    output_conf = config['outputs']

    ######## Load Model ########
    global_conf = config["global"]
    weights_file = global_conf['weights_file']

    model = load_model(config)
    model.load_weights(weights_file)

    eval_metrics = OrderedDict()
    for mobj in config['metrics']:
        mobj = mobj.lower()
        if '@' in mobj:
            mt_key, mt_val = mobj.split('@', 1)
            eval_metrics[mobj] = metrics.get(mt_key)(int(mt_val))
        else:
            eval_metrics[mobj] = metrics.get(mobj)
    res = dict([[k,0.] for k in eval_metrics.keys()])

    for tag, generator in predict_gen.items():
        genfun = generator.get_batch_generator()
        print '[Predict] @ %s ' % tag,
        num_valid = 0
        res_scores = {} 
        for input_data, y_true in genfun:
            y_pred = model.predict(input_data, batch_size=len(y_true) )

            for k, eval_func in eval_metrics.items():
                res[k] += eval_func(y_true = y_true, y_pred = y_pred)

            y_pred = np.squeeze(y_pred)
            for p, y, t in zip(input_data['ID'], y_pred, y_true):
                if p[0] not in res_scores:
                    res_scores[p[0]] = {}
                res_scores[p[0]][p[1]] = (y, t)

            num_valid += 1
        generator.reset()

        if tag in output_conf:
            if output_conf[tag]['save_format'] == 'TREC':
                with open(output_conf[tag]['save_path'], 'w') as f:
                    for qid, dinfo in res_scores.items():
                        dinfo = sorted(dinfo.items(), key=lambda d:d[1][0], reverse=True)
                        for inum,(did, (score, gt)) in enumerate(dinfo):
                            print >> f, '%s\tQ0\t%s\t%d\t%f\t%s'%(qid, did, inum, score, config['net_name'])
            elif output_conf[tag]['save_format'] == 'TEXTNET':
                with open(output_conf[tag]['save_path'], 'w') as f:
                    for qid, dinfo in res_scores.items():
                        dinfo = sorted(dinfo.items(), key=lambda d:d[1][0], reverse=True)
                        for inum,(did, (score, gt)) in enumerate(dinfo):
                            print >> f, '%s %s %s %s'%(gt, qid, did, score)

        print '[Predict] results: ', '  '.join(['%s:%f'%(k,v/num_valid) for k, v in res.items()])
        sys.stdout.flush()

def main(argv):
    """The main function

    # Arguments
            argv: Including two parts:the phase(train or predict) and the file of model
                argv can express like this:(--phase train --model_file models/arci.config)
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', default='train', help='Phase: Can be train or predict, the default value is train.')
    parser.add_argument('--model_file', default='./models/matchzoo.model', help='Model_file: MatchZoo model file for the chosen model.')
    args = parser.parse_args()
    model_file =  args.model_file
    with open(model_file, 'r') as f:
    # This will get the configuration information of the model
        config = json.load(f)
    phase = args.phase
    if args.phase == 'train':
        train(config)
    elif args.phase == 'predict':
        predict(config)
    else:
        print 'Phase Error.'
    return

if __name__=='__main__':
    main(sys.argv)
