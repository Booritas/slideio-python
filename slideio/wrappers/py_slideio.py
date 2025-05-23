'''Slideio python module.

Slideio is a python module for the reading of medical images. It allows reading whole slides as well as any region of a slide.
Large slides can be effectively scaled to a smaller size.
The module uses internal zoom pyramids of images to make the scaling process as fast as possible.
Slideio supports 2D slides as well as 3D data sets and time series.
'''
import sys
import os

from ..core import core_convert_scene, core_convert_scene_ex, core_open_slide, core_transform_scene, core_set_log_level, core_get_driver_ids, core_get_version

class Scene(object):
    '''slideio Scene class.

    Scene class represents a single 2D-4D image from a Slide object.
    The class implements methods for accessing the image raster and metadata.
    All raster channels of the scene have the same resolution and the same size.
    Raster channels may have different data types depending on the image format.
    A scene can represent a separate region of interest of the slide.
    A Scene object can be created by a "get_scene" method of a Slide object or by using the constructor: 

    scene = Scene(slide, scene_index)    
    '''
    def __init__(self, scene):
        '''Creates an instance of Scene class.
        Args:
            scene: Instance of CoreScene class.
        '''
        self.scene = scene

    def __repr__(self):
        return self.scene.__repr__()

    def __del__(self):
        if self.scene is not None:
            del self.scene
            self.scene = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__del__()

    @property
    def name(self):
        '''Scene name extracted from slide metadata."'''
        return self.scene.name

    @property
    def compression(self):
        '''Compression method for the scene raster data.'''
        return self.scene.compression

    @property
    def file_path(self):
        '''File path to the scene. In the most cases the same as file path of the slide.'''
        return self.scene.file_path

    @property
    def magnification(self):
        '''Scanning magnification extracted from the slide metadata.'''
        return self.scene.magnification

    @property
    def num_channels(self):
        '''Number of raster channels in the scene raster data.'''
        return self.scene.num_channels

    @property
    def num_t_frames(self):
        '''Number of time frames in the scene raster data.'''
        return self.scene.num_t_frames

    @property
    def num_z_slices(self):
        '''Number slices along Z axis in the scene raster data.'''
        return self.scene.num_z_slices

    @property
    def rect(self):
        '''Scene rectangle in pixels. A tuple (x-origin, y-origin, width, height).'''
        return self.scene.rect

    @property
    def size(self):
        '''Scene size in pixels. A tuple (width, height).'''
        rc = self.scene.rect
        return (rc[2], rc[3])
    
    @property
    def origin(self):
        '''Coordinates of the top left corner of the scene. A tuple (x, y).'''
        rc = self.scene.rect
        return (rc[0], rc[1])

    @property
    def resolution(self):
        '''Scene resolution in meters per pixel (pixel size in meters). A tuple (x-res, y-res)'''
        return self.scene.resolution

    @property
    def t_resolution(self):
        '''Time distance between two time-frames in seconds.'''
        return  self.scene.t_resolution

    @property
    def z_resolution(self):
        '''Distance between two Z-slices in meters.'''
        return self.scene.z_resolution

    @property
    def num_aux_images(self):
        '''Number of auxiliary images of the scene.'''
        return self.scene.num_aux_images

    @property
    def num_zoom_levels(self):
        '''Number of zoom levels in internal image pyramid.'''
        return self.scene.num_zoom_levels

    @property
    def metadata_format(self):
        '''Get format of the metadata of the scene'''
        return self.scene.format_metadata()

    def get_zoom_level_info(self, index):
        '''Get information about a level in the internal image pyramid.'''
        return self.scene.get_zoom_level_info(index)

    def get_aux_image_names(self):
        '''Get list of auxiliary image names'''
        return self.scene.get_aux_image_names()

    def get_raw_metadata(self):
        '''Get raw metadata of the scene'''
        return self.scene.get_raw_metadata()

    def get_aux_image(self, image_name, size=(0,0), channel_indices=[]):
        '''Get auxiliary image as a numpy array.

        Args:
            image_name: name of the auxiliary image
            channel_indices: array of channel indices to be retrieved. [] - all channels.
            size: size of the block after rescaling. (0,0) - no scaling.
        '''
        scene = self.scene.get_aux_image(image_name)
        return scene.read_block(rect=(0,0,0,0), size=size, channel_indices=channel_indices, slices=(0,1), frames=(0,1))

    def read_block(self, rect=(0,0,0,0), size=(0,0), channel_indices=[], slices=(0,1), frames=(0,1)):
        '''Reads rectangular block of the scene with optional rescaling.

        Args:
            rect: block rectangle, defined as a tuple (x, y, widht, height), where x,y - pixel coordinates of the  top left corner of the block relatively to the scene top left corner, width, height - block width and height
            size: size of the block after rescaling. (0,0) - no scaling.
            channel_indices: array of channel indices to be retrieved. [] - all channels.
            slices: range of z slices (first, last+1) to be retrieved. (0,3) for 0,1,2 slices. (0,0) for the first slice only.
            frames: range of time frames (first, last+1) to be retrieved.

        Returns:
            numpy array with pixel values
        '''
        return self.scene.read_block(rect, size, channel_indices, slices, frames)

    def get_channel_data_type(self, channel):
        '''Returns data type for a scene channel by index
        Args:
            channel: channel index.
        '''
        return self.scene.get_channel_data_type(channel)

    def get_channel_name(self, channel):
        '''Returns name of a scene channel by index
        Args:
            channel: channel index.
        '''
        return self.scene.get_channel_name(channel)

    def save_image(self, params, output_path, callback=None):
        '''Save scene image to a file
        Args:
            params: image format of the output file
            output_path: path to the output file
            callback: callback progress function
        '''
        if(callback is None):
            core_convert_scene(self.scene, params, output_path)
        else:
            core_convert_scene_ex(self.scene, params, output_path, callback)

    def apply_transformation(self, transormation):
        '''Transform scene raster
        
        Args:
            transformation: transformation parameters
        '''
        transformed = core_transform_scene(self.scene, transormation)
        new_scene = Scene(transformed)
        return new_scene

class Slide(object):
    '''Slide class represents slides, normally a single image file or a folder.
    Slide contains a collection of scenes - separate images.
    '''
    def __init__(self, path:str, driver:str):
        self.slide = core_open_slide(path, driver)

    def __repr__(self):
        return self.slide.__repr__()

    def __del__(self):
        if hasattr(self, 'slide'):
            if self.slide is not None:
                del self.slide
                self.slide = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__del__()

    def get_scene(self, index):
        '''Return slide scene by index'''
        scene = Scene(self.slide.get_scene(index))
        return scene
    
    def get_scene_by_name(self, name):
        '''Return slide scene by name'''
        scene = Scene(self.slide.get_scene_by_name(name))
        return scene
    
    @property
    def num_scenes(self) -> int:
        '''Number of scenes in the slide'''
        return self.slide.num_scenes

    @property
    def raw_metadata(self) -> str:
        '''Raw metadata extracted from the slide'''
        return self.slide.raw_metadata

    @property
    def metadata_format(self) -> str:
        '''Format of the slide metadata'''
        return self.slide.metadata_format

    @property
    def file_path(self):
        '''Returns path to the slide file/folder'''
        return self.slide.file_path

    @property
    def num_aux_images(self):
        '''Number of auxiliary images of the slide.'''
        return self.slide.num_aux_images

    def get_aux_image_names(self):
        '''Get list of auxiliary image names'''
        return self.slide.get_aux_image_names()

    def get_aux_image_raster(self, image_name, size=(0,0), channel_indices=[]):
        '''Get auxiliary image as numpy array.

        Args:
            image_name: name of the auxiliary image
            channel_indices: array of channel indices to be retrieved. [] - all channels.
            size: size of the block after rescaling. (0,0) - no scaling.
        '''
        scene = self.slide.get_aux_image(image_name)
        return scene.read_block(rect=(0,0,0,0), size=size, channel_indices=channel_indices, slices=(0,1), frames=(0,1))

    def get_aux_image(self, image_name):
        '''Get auxiliary image as Scene object.

        Args:
            image_name: name of the auxiliary image
        '''
        scene = Scene(self.slide.get_aux_image(image_name))
        return scene


def convert_scene(scene, params, output_path, callback=None):
    '''Save scene to a file with conversion
    
    Args:
        scene: origin scene
        params: image format of the output file
        output_path: path to the output file
        callback: callback progress function
    '''
    if(callback is None):
        core_convert_scene(scene.scene, params, output_path)
    else:
        core_convert_scene_ex(scene.scene, params, output_path, callback)

def open_slide(path:str, driver:str='AUTO'):
    '''Returns an instance of a slide object

    Args:
        path: a path to the image file
        driver: name of the driver or "AUTO" for automatic driver selection
    '''
    slide = Slide(path, driver)
    return slide

def get_driver_ids():
    '''Returns a list of ids of available image drivers'''
    return core_get_driver_ids()

def compare_images(left, right):
    '''Compares two images represented by numpy arrays'''
    return core_compare_images(left, right)

def set_log_level(log_level:str):
    '''Sets log level'''
    core_set_log_level(log_level)

def transform_scene(scene, params):
    '''Transform scene raster
    
    Args:
        scene: origin scene
        params: transformation parameters
    '''
    internal_scene = scene.scene
    transformed = core_transform_scene(internal_scene, params)
    new_scene = Scene(transformed)
    return new_scene

def get_version():
    '''Returns version of the slideio library'''
    return core_get_version()

