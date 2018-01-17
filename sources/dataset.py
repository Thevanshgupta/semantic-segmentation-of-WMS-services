#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
/**
 *   Raphael Delhome - december 2017
 *
 *   This library is free software; you can redistribute it and/or
 *   modify it under the terms of the GNU Library General Public
 *   License as published by the Free Software Foundation; either
 *   version 2 of the License, or (at your option) any later version.
 *   
 *   This library is distributed in the hope that it will be useful,
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 *   Library General Public License for more details.
 *   You should have received a copy of the GNU Library General Public
 *   License along with this library; if not, see <http://www.gnu.org/licenses/>
 */
"""

from collections import defaultdict
import cv2
from PIL import Image
import json
import math
import numpy as np
import os

import utils

class Dataset(object):

    def __init__(self, image_size, glossary_filename):
        """ Class constructor
        """
        self.image_size = image_size
        self.class_info = defaultdict()
        self.build_glossary(glossary_filename)
        self.image_info = defaultdict()

    def get_class(self, class_id):
        """ `class_info` getter, return only one class

        Parameters:
        -----------
        class_id: integer
            Id of the dataset class that must be returned
        """
        if not class_id in self.class_info.keys():
            print("Class {} not in the dataset glossary".format(class_id))
            return None
        return self.class_info[class_id]
    
    def get_image(self, image_id):
        """ `image_info` getter, return only the information for one image

        Parameters:
        -----------
        image_id: integer
            Id of the dataset image that must be returned
        """
        if not image_id in self.image_info.keys():
            print("Image {} not in the dataset".format(image_id))
            return None
        return self.image_info[image_id]

    def get_nb_class(self):
        """ `class_info` getter, return the size of `class_info`, i.e. the
        number of class in the dataset
        """
        return len(self.class_info)

    def get_nb_images(self):
        """ `image_info` getter, return the size of `image_info`, i.e. the
        number of images in the dataset
        """
        return len(self.image_info)

    def get_class_popularity(self):
        """
        """
        labels = [self.image_info[im]["labels"]
                  for im in self.image_info.keys()]
        if self.get_nb_images() == 0:
            utils.logger.info("No images in the dataset.")
            return None
        else:
            return np.round(np.divide(sum(np.array(labels)),
                                      self.get_nb_images()), 3)

    def build_glossary(self, config_filename):
        """Read the Mapillary glossary stored as a json file at the data
        repository root

        Parameter:
        ----------
        config_filename: object
            String designing the relative path of the dataset glossary
        (based on Mapillary dataset)
        """
        with open(config_filename) as config_file:
            glossary = json.load(config_file)
        if "labels" not in glossary.keys():
            print("There is no 'label' key in the provided glossary.")
            return None
        for lab_id, label in enumerate(glossary["labels"]):
            if label["evaluate"]:
                name_items = label["name"].split('--')
                category = '-'.join(name_items[:-1])
                self.add_class(lab_id, name_items[-1], label["color"], category)

    def add_class(self, class_id, class_name, color, category=None):
        """ Add a new class to the dataset with class id `class_id`

        Parameters:
        -----------
        class_id: integer
            Id of the new class
        class_name: object
            String designing the new class name
        color: list
            List of three integers (between 0 and 255) that characterizes the
        class (useful for semantic segmentation result printing)
        category: object
            String designing the category of the dataset class
        """
        if class_id in self.class_info.keys():
            print("Class {} already stored into the class set.".format(class_id))
            return None
        self.class_info[class_id] = {"name": class_name,
                                     "category": category,
                                     "color": color}

    def populate(self, datadir):
        """ Populate the dataset with images contained into `datadir` directory
 
       Parameter:
        ----------
        datadir: object
            String designing the relative path of the directory that contains
        new images
        """
        utils.make_dir(os.path.join(datadir, "input"))
        image_dir = os.path.join(datadir, "images")
        image_list = os.listdir(image_dir)
        image_list_longname = [os.path.join(image_dir, l) for l in image_list]
        for image_id, image_filename in enumerate(image_list_longname):
            label_filename = image_filename.replace("images/", "labels/")
            label_filename = label_filename.replace(".jpg", ".png")

            # open original images
            img_in = Image.open(image_filename)
            old_width, old_height = img_in.size
            img_out = Image.open(label_filename)

            # resize images (self.image_size*larger_size or larger_size*self.image_size)
            img_in = utils.resize_image(img_in, self.image_size)
            img_out = utils.resize_image(img_out, self.image_size)

            # crop images to get self.image_size*self.image_size dimensions
            crop_pix = np.random.randint(0, 1+max(img_in.size)-self.image_size)
            final_img_in = utils.mono_crop_image(img_in, crop_pix)
            final_img_out = utils.mono_crop_image(img_out, crop_pix)
            resizing_ratio = math.ceil(old_width * old_height
                                       / (self.image_size**2))

            # save final image
            new_filename = image_filename.replace("images/", "input/")
            final_img_in.save(new_filename)

            # label_filename vs label image
            labels = utils.mapillary_label_building(final_img_out,
                                                    self.get_nb_class())

            # add to dataset object
            self.add_image(image_id, image_filename, new_filename,
                           label_filename, labels)


    def add_image(self, image_id, raw_filename, image_filename,
                  label_filename, labels):
        """ Add a new image to the dataset with image id `image_id`; an image
                  in the dataset is represented by an id, an original filename,
                  a new version filename (the image is preprocessed), a label
                  filename for getting ground truth description and a list of
                  0-1 labels (1 if the i-th class is on the image, 0 otherwise)

        Parameters:
        -----------
        image_id: integer
            Id of the new image
        raw_filename: object
            String designing the new image original name on the file system
        image_filename: object
            String designing the new preprocessed image name on the file system
        label_filename: object
            String designing the new image ground-truth-version name on the
        file system
        labels: list
            List of 0-1 values, the i-th value being 1 if the i-th class is on
        the new image, 0 otherwise; the label list length correspond to the
        number of classes in the dataset
        """
        if image_id in self.image_info.keys():
            print("Image {} already stored into the class set.".format(image_id))
            return None
        self.image_info[image_id] = {"raw_filename": raw_filename,
                                     "image_filename": image_filename,
                                     "label_filename": label_filename,
                                     "labels": labels}

    def save(self, filename):
        """Save dataset in a json file indicated by `filename`

        Parameter
        ---------
        filename: object
            String designing the relative path where the dataset must be saved
        """
        with open(filename, 'w') as fp:
            json.dump({"image_size": self.image_size,
                       "classes": self.class_info,
                       "images": self.image_info}, fp)
        utils.logger.info("The dataset has been saved into {}".format(filename))

    def load(self, filename):
        """Load a dataset from a json file indicated by `filename`

        Parameter
        ---------
        filename: object
            String designing the relative path from where the dataset must be
        loaded
        """
        with open(filename) as fp:
            ds = json.load(fp)
            self.image_size = ds["image_size"]
            self.class_info = {int(k):ds["classes"][k] for k in ds["classes"].keys()}
            self.image_info = {int(k):ds["images"][k] for k in ds["images"].keys()}
        utils.logger.info("The dataset has been loaded from {}".format(filename))

class ShapeDataset(Dataset):

    def __init__(self, image_size, nb_classes):
        """ Class constructor
        """
        self.image_size = image_size
        self.class_info = defaultdict()
        self.build_glossary(nb_classes)
        self.image_info = defaultdict()
        self.pixel_mean = [0, 0, 0]
        self.pixel_std = [1, 1, 1]

    def build_glossary(self, nb_classes):
        """Read the shape glossary stored as a json file at the data
        repository root

        Parameter:
        ----------
        nb_classes: integer
            Number of shape types (either 1, 2 or 3, warning if more)
        """
        self.add_class(0, "square", [0, 10, 10])
        if nb_classes > 1:
            self.add_class(1, "circle", [200, 10, 50])
        if nb_classes > 2:
            self.add_class(2, "triangle", [100, 50, 50])
        if nb_classes > 3:
            utils.logger.warning("Only three classes are considered.")

    def generate_labels(self, nb_images):
        """ Generate random shape labels in order to prepare shape image
        generation; use numpy to generate random indices for each labels, these
        indices will be the positive examples; return a 2D-list

        Parameter:
        ----------
        nb_images: integer
            Number of images to label in the dataset
        """
        raw_labels = [np.random.choice(np.arange(nb_images),
                                            int(nb_images/2),
                                            replace=False)
                      for i in range(self.get_nb_class())]
        labels = np.zeros([nb_images, self.get_nb_class()], dtype=int)
        for i in range(self.get_nb_class()):
            labels[raw_labels[i], i] = 1
        return labels.tolist()

    def populate(self, datapath, nb_images=10000, buf=8):
        """ Populate the dataset with images contained into `datadir` directory

       Parameter:
        ----------
        datapath: object
            String designing the relative path of the directory that contains
        new images
        nb_images: integer
            Number of images that must be added in the dataset
        buf: integer
            Minimal number of pixels between shape base point and image borders
        """
        shape_gen = self.generate_labels(nb_images)
        for i, image_label in enumerate(shape_gen):
            bg_color = np.random.randint(0, 255, 3).tolist()
            shape_specs = []
            for l in image_label:
                if l:
                    shape_color = np.random.randint(0, 255, 3).tolist()
                    x, y = np.random.randint(buf, self.image_size - buf - 1, 2).tolist()
                    shape_size = np.random.randint(buf, self.image_size // 4)
                    shape_specs.append([shape_color, x, y, shape_size])
                else:
                    shape_specs.append([None, None, None, None])
            self.add_image(i, bg_color, shape_specs, image_label)
            self.draw_image(i, datapath)
        self.compute_mean_pixel()

    def add_image(self, image_id, background, specifications, labels):
        """ Add a new image to the dataset with image id `image_id`; an image
        in the dataset is represented by an id, a list of shape specifications,
        a background color and a list of 0-1 labels (1 if the i-th class is on
        the image, 0 otherwise)

        Parameters:
        -----------
        image_id: integer
            Id of the new image
        background: list
            List of three integer between 0 and 255 that designs the image
        background color
        specifications: list
            Image specifications, as a list of shapes (color, coordinates and
        size)
        labels: list
            List of 0-1 values, the i-th value being 1 if the i-th class is on
        the new image, 0 otherwise; the label list length correspond to the
        number of classes in the dataset
        """
        if image_id in self.image_info.keys():
            print("Image {} already stored into the class set.".format(image_id))
            return None
        self.image_info[image_id] = {"background": background,
                                     "shape_specs": specifications,
                                     "labels": labels}

    def draw_image(self, image_id, datapath):
        """Draws an image from the specifications of its shapes and saves it on
        the file system to `datapath`

        Parameters
        ----------
        image_id: integer
            Image id
        datapath: object
            String that characterizes the repository in which images will be stored
        """
        utils.make_dir(datapath[:datapath.rfind("/")])
        utils.make_dir(datapath)
        image_info = self.image_info[image_id]

        image = np.ones([self.image_size, self.image_size, 3], dtype=np.uint8)
        image = image * np.array(image_info["background"], dtype=np.uint8)

        # Get the center x, y and the size s
        if image_info["labels"][0]:
            color, x, y, s = image_info["shape_specs"][0]
            color = tuple(map(int, color))
            image = cv2.rectangle(image, (x - s, y - s), (x + s, y + s), color, -1)
        if image_info["labels"][1]:
            color, x, y, s = image_info["shape_specs"][1]
            color = tuple(map(int, color))
            image = cv2.circle(image, (x, y), s, color, -1)
        if image_info["labels"][2]:
            color, x, y, s = image_info["shape_specs"][2]
            color = tuple(map(int, color))
            x, y, s = map(int, (x, y, s))
            points = np.array([[(x, y - s),
                                (x - s / math.sin(math.radians(60)), y + s),
                                (x + s / math.sin(math.radians(60)), y + s),]],
                              dtype=np.int32)
            image = cv2.fillPoly(image, points, color)
        image_filename = os.path.join(datapath, "shape_{:05}.png".format(image_id))
        self.image_info[image_id]["image_filename"] = image_filename
        cv2.imwrite(image_filename, image)

    def compute_mean_pixel(self):
        """Compute mean and standard deviation of dataset images, for each
        RGB-channel
        """
        mean_pixels, std_pixels = [], []
        for image_id in self.image_info.keys():
            image_filename = self.image_info[image_id]["image_filename"]
            mean_pixels.append(np.mean(np.array(Image.open(image_filename)),
                                       axis=(0,1)))
            std_pixels.append(np.std(np.array(Image.open(image_filename)),
                                     axis=(0,1)))
        self.pixel_mean = np.mean(np.array(mean_pixels), axis=0)
        self.pixel_std = np.std(np.array(std_pixels), axis=0)
