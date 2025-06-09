# Import necessary GStreamer libraries and DeepStream python bindings
import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst, GLib
import pyds

# Initialize GStreamer
Gst.init(None)

# Create Pipeline element that will form a connection of other elements
pipeline=Gst.Pipeline()
print('Created pipeline')

# Create Source element for reading from a file and set the location property
source=Gst.ElementFactory.make("filesrc", "file-source")
source.set_property('location', target_video_path)

# Create H264 Parser with h264parse as the input file is an elementary h264 stream
h264parser=Gst.ElementFactory.make("h264parse", "h264-parser")

# Create Decoder with nvv4l2decoder for accelerated decoding on GPU
decoder=Gst.ElementFactory.make("nvv4l2decoder", "nvv4l2-decoder")

# Create Streamux with nvstreammux to form batches for one or more sources and set properties
streammux=Gst.ElementFactory.make("nvstreammux", "stream-muxer")
streammux.set_property('width', 888) 
streammux.set_property('height', 696) 
streammux.set_property('batch-size', 1)

# Create Primary GStreamer Inference Element with nvinfer to run inference on the decoder's output after batching
pgie=Gst.ElementFactory.make("nvinfer", "primary-inference")

# Create Sink with fakesink as the end point of the pipeline
fakesink=Gst.ElementFactory.make('fakesink', 'fakesink')
fakesink.set_property('sync', 1)
print('Created elements')

# Add elements to pipeline
pipeline.add(source)
pipeline.add(h264parser)
pipeline.add(decoder)
pipeline.add(streammux)
pipeline.add(pgie)
pipeline.add(fakesink)
print('Added elements to pipeline')

# Link elements in the pipeline
source.link(h264parser)
h264parser.link(decoder)

# Link decoder source pad to streammux sink pad
decoder_srcpad=decoder.get_static_pad("src")    
streammux_sinkpad=streammux.get_request_pad("sink_0")
decoder_srcpad.link(streammux_sinkpad)

# Link the rest of the elements in the pipeline
streammux.link(pgie)
pgie.link(fakesink)
print('Linked elements in pipeline')
