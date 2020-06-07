import cv2
import numpy as np
import scipy.signal as sig

def blockshaped(arr, nrows, ncols):
    """
    Return an array of shape (n, nrows, ncols) where
    n * nrows * ncols = arr.size

    If arr is a 2D array, the returned array should look like n subblocks with
    each subblock preserving the "physical" layout of arr.
    """
    h, w = arr.shape
    assert h % nrows == 0, "{} rows is not evenly divisble by {}".format(h, nrows)
    assert w % ncols == 0, "{} cols is not evenly divisble by {}".format(w, ncols)
    return (arr.reshape(h//nrows, nrows, -1, ncols)
               .swapaxes(1,2)
               .reshape(-1, nrows, ncols))

def divide_in_tiles(frame, tile_size=10):
    return blockshaped(frame, tile_size, tile_size)

def convert_and_resize(frame, dim):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, dim)
    
    return resized


def gradients(frames):
    total_frames = frames.shape[2]
    
    merged_gradients = np.array([])
    
    framesDx = []
    framesDy = []
    framesDt = []
    
    convDt = sig.convolve(frames, np.array([[[1,0,-1]]]), mode='same')
    
    for frame_num in range(0, total_frames):
        frame_convDx = sig.convolve(frames[:,:,frame_num], np.array([[1, 0, -1]]), mode='same')
        frame_convDy = sig.convolve(frames[:,:,frame_num], np.array([[1], [0], [-1]]), mode='same')
        frame_convDt = convDt[:,:,frame_num]
        framesDx.append(frame_convDx)
        framesDy.append(frame_convDy)
        framesDt.append(frame_convDt)  
        
        frame_gradient = np.stack((frame_convDx,frame_convDy,frame_convDt), axis=2).flatten()
        merged_gradients = np.concatenate((merged_gradients, frame_gradient), axis=None)
    
    return framesDx,framesDy,framesDt,merged_gradients


def spatiotemporal_cubes(frames, dim):
    tiled_frames = []
    for frame in frames:
        converted_frame = convert_and_resize(frame, dim)
        tiled_frames.append(divide_in_tiles(converted_frame))
    
    
    
    return np.stack(tuple(tiled_frames), axis=3)



def video_sequence_cubes_and_gradients(frames,dim,cube_depth,tile_size):
    num_frames = len(frames)
    total_sequences = int(num_frames/cube_depth)
    
    total_tiles = int((dim[0]/tile_size) * (dim[1]/tile_size))
    size_gradients_flattened = tile_size*tile_size*cube_depth*3
    
    all_cubes = np.zeros((total_tiles,tile_size,tile_size,cube_depth))
    all_gradients = np.zeros((total_tiles, size_gradients_flattened))
    
    cubes = spatiotemporal_cubes(frames, dim)
    all_cubes = cubes

    cube_gradient = np.zeros((cubes.shape[0], size_gradients_flattened))
    for cube_number in range(0,cubes.shape[0]):
        cube_gradient[cube_number] = gradients(cubes[cube_number])[3]
    all_gradients = cube_gradient
        
    return all_cubes, all_gradients


def generate_features(frame_sequence,cube_depth,tile_size):
    #opencv is y,x
    #https://stackoverflow.com/questions/21248245/opencv-image-resize-flips-dimensions/22094421
    dimensions = [(20,20), (160,120), (40,30)]
    
    features = []
    
    for dim in dimensions:
        features.append(video_sequence_cubes_and_gradients(frame_sequence,dim,cube_depth,tile_size)[1])
        
    return np.concatenate(features, axis=0)

def process_frames(frames,cube_depth=5,tile_size=10):
    num_frames = len(frames)
    total_sequences = int(num_frames/cube_depth)
    
    sequence_features = []
    
    
    for i in range(0,total_sequences):
        frames_slice = frames[i*cube_depth:i*cube_depth + cube_depth]
    
        sequence_features.append(generate_features(frames_slice,cube_depth,tile_size))
    
    result = np.array(sequence_features) #shape (total_sequences, cubes, gradients) Lu et al applies PCA to reduce the gradients dimension
    return result.reshape(result.shape[0], result.shape[1]*result.shape[2]) #shape (total_sequences, features)


