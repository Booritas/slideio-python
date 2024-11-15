import sys
#sys.path.insert(1, r'/Users/s.melnikov/projects/slideio/slideio-python/build/OSX/debug/bin')
#from memory_profiler import profile
#import slideiopybind as sld
import slideio as sld

slide = sld.open_slide('/slideio/images/slideio_extra/testdata/cv/slideio/zvi/Zeiss-1-Merged.zvi','ZVI')
scene = slide.get_scene(0)
print(scene)
scene.read_block(slices=(0,3))