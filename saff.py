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

# Declare list to hold count data
obj_counts=[]

# Define the Probe Function
def pgie_src_pad_buffer_probe(pad, info):
    gst_buffer=info.get_buffer()

    # Retrieve batch metadata from the gst_buffer
    # Note that pyds.gst_buffer_get_nvds_batch_meta() expects the
    # C address of gst_buffer as input, which is obtained with hash(gst_buffer)
    batch_meta=pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
    l_frame=batch_meta.frame_meta_list
    
    # Iterate through each frame in the batch metadata until the end
    while l_frame is not None:
        try:
            frame_meta=pyds.NvDsFrameMeta.cast(l_frame.data)
        except StopIteration:
            break

        frame_num=frame_meta.frame_num
        num_obj=frame_meta.num_obj_meta
        l_obj=frame_meta.obj_meta_list
        
        print("Frame Number={} Number of Objects={}".format(frame_num, num_obj))
        
        # Append number of objects a list 
        obj_counts.append(num_obj)
        
        # Iterate through each object in the frame metadata until the end
        while l_obj is not None:
            try:
                obj_meta=pyds.NvDsObjectMeta.cast(l_obj.data)
                print('\t Object: {} - Top: {}, Left: {}, Width: {}, Height: {}'.format(obj_meta.obj_label, \
                                                                                        round(obj_meta.rect_params.top), \
                                                                                        round(obj_meta.rect_params.left), \
                                                                                        round(obj_meta.rect_params.width), \
                                                                                        round(obj_meta.rect_params.height)))
            except StopIteration:
                break
            
            try: 
                l_obj=l_obj.next
            except StopIteration:
                break
        
        try:
            l_frame=l_frame.next
        except StopIteration:
            break
    return Gst.PadProbeReturn.OK

# Add probe to inference plugin's source
pgie_src_pad=pgie.get_static_pad('src')
probe_id=pgie_src_pad.add_probe(Gst.PadProbeType.BUFFER, pgie_src_pad_buffer_probe)
print('Attached probe')
