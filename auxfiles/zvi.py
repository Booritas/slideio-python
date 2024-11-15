import sys
#sys.path.insert(1, r'/Users/s.melnikov/projects/slideio/slideio-python/build/OSX/debug/bin')
#from memory_profiler import profile
import cv2 as cv
import slideiopybind as sld

slide = sld.open_slide('/slideio/images/slideio_extra/testdata/cv/slideio/zvi/Zeiss-1-Stacked.zvi','ZVI')
scene = slide.get_scene(0)
print(scene)
scene.read_block(slices=(0,3))