import torch
import shutil
import os
import numpy as np
from config import Config


class ModelCheckpoint:
    def __init__(self, weight_dir='./weights', config=Config):
        self.weight_dir = weight_dir
        self.config = config
        file_prefix = ''
        self.filename = os.path.join(self.weight_dir, file_prefix + 'model_latest_checkpoint.pth.tar')
        self.best_filename = os.path.join(self.weight_dir, file_prefix + 'model_best.pth.tar')

    def save(self, is_best, min_val_error, num_bad_epochs, epoch, model, optimizers, schedulers=None):
        scheduler_save = schedulers if schedulers is None else [sch.state_dict() for sch in schedulers]
        save_dict = {
            'model': model.state_dict(),
            'optimizers': [opt.state_dict() for opt in optimizers],
            'epoch': epoch,
            'min_val_error': min_val_error,
            'num_bad_epochs': num_bad_epochs,
            'schedulers': scheduler_save
        }
        torch.save(save_dict, self.filename)
        if is_best:
            shutil.copyfile(self.filename, self.best_filename)

    def load(self, model, optimizers=None, schedulers=None, load_best=False):
        load_filename = self.best_filename if load_best else self.filename
        if os.path.isfile(load_filename):
            checkpoint = torch.load(load_filename, map_location=self.config.device)
            model.load_state_dict(checkpoint['model'])
            if optimizers is not None:
                optimizers = [opt.load_state_dict(checkpoint['optimizers'][idx]) for idx, opt in enumerate(optimizers)]
            if schedulers is not None:
                schedulers = [sch.load_state_dict(checkpoint['schedulers'][idx]) for idx, sch in enumerate(schedulers)]
            start_epoch = checkpoint['epoch'] + 1
            min_val_error = checkpoint['min_val_error']
            num_bad_epochs = checkpoint['num_bad_epochs']
        else:
            raise FileNotFoundError(f'No checkpoint found at {load_filename}')

        return model, optimizers, schedulers, [start_epoch, min_val_error, num_bad_epochs]


class EarlyStopping(object):
    """
    author:https://github.com/stefanonardo
    source: https://gist.github.com/stefanonardo/693d96ceb2f531fa05db530f3e21517d
    """
    def __init__(self, mode='min', min_delta=0, patience=10, percentage=False):
        self.mode = mode
        self.min_delta = min_delta
        self.patience = patience
        self.best = None
        self.num_bad_epochs = 0
        self.is_better = None
        self._init_is_better(mode, min_delta, percentage)

        if patience == 0:
            self.is_better = lambda a, b: True
            self.step = lambda a: False

    def step(self, metrics):
        if self.best is None:
            self.best = metrics
            return False

        if np.isnan(metrics):
            return True

        if self.is_better(metrics, self.best):
            self.num_bad_epochs = 0
            self.best = metrics
        else:
            self.num_bad_epochs += 1

        if self.num_bad_epochs >= self.patience:
            return True

        return False

    def _init_is_better(self, mode, min_delta, percentage):
        if mode not in {'min', 'max'}:
            raise ValueError('mode ' + mode + ' is unknown!')
        if not percentage:
            if mode == 'min':
                self.is_better = lambda a, best: a < best - min_delta
            if mode == 'max':
                self.is_better = lambda a, best: a > best + min_delta
        else:
            if mode == 'min':
                self.is_better = lambda a, best: a < best - (
                            best * min_delta / 100)
            if mode == 'max':
                self.is_better = lambda a, best: a > best + (
                            best * min_delta / 100)
