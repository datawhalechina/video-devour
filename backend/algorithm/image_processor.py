# backend/algorithm/image_processor.py
import os
import shutil
import logging
import config

try:
    import cv2
    from skimage.metrics import structural_similarity as ssim
    IMAGE_LIBS_AVAILABLE = True
except ImportError:
    IMAGE_LIBS_AVAILABLE = False

def _process_single_directory(directory, similarity_threshold=0.8):
    """
    Processes images in a single directory: resize, compare, and delete redundant frames.
    """
    logging.info(f"开始处理目录: {directory}")
    
    image_files = sorted([f for f in os.listdir(directory) if f.endswith('.jpg')])
    
    if not image_files:
        logging.info("该目录下没有找到图片。")
        return

    # First, resize all images
    for filename in image_files:
        filepath = os.path.join(directory, filename)
        try:
            img = cv2.imread(filepath)
            if img is None: continue
            resized_img = cv2.resize(img, (img.shape[1] // 2, img.shape[0] // 2), interpolation=cv2.INTER_AREA)
            cv2.imwrite(filepath, resized_img, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
        except Exception as e:
            logging.error(f"处理图片 {filepath} 时出错: {e}")
            
    # Start deduplication
    i = 0
    while i < len(image_files) - 1:
        img1_path = os.path.join(directory, image_files[i])
        img2_path = os.path.join(directory, image_files[i+1])

        try:
            img1 = cv2.imread(img1_path, cv2.IMREAD_GRAYSCALE)
            img2 = cv2.imread(img2_path, cv2.IMREAD_GRAYSCALE)
            
            if img1 is None or img2 is None:
                i += 1
                continue
            
            similarity = ssim(img1, img2)
            
            if similarity > similarity_threshold:
                os.remove(img2_path)
                logging.info(f"删除冗余图片: {image_files[i+1]} (与 {image_files[i]} 相似度: {similarity:.2f})")
                image_files.pop(i + 1)
            else:
                i += 1
        except Exception as e:
            logging.error(f"比较图片 {image_files[i]} 和 {image_files[i+1]} 时出错: {e}")
            i += 1

    # Ensure at least one image remains
    if not os.listdir(directory) and image_files:
        # Restore the first image if all were deleted
        first_image_original_path = os.path.join(directory, image_files[0])
        # This part is tricky as the file might be gone. The logic should be to prevent deletion instead.
        # Let's adjust the loop condition to prevent deleting the last image.
        # The current logic will retain the first image if all others are similar to it.
        pass
    
    logging.info(f"目录 {directory} 处理完成")

def process_all_frames():
    """
    Main function to process all extracted frames, checking for dependencies first.
    """
    if not IMAGE_LIBS_AVAILABLE:
        logging.warning("跳过帧处理。请安装必要的库: pip install opencv-python-headless scikit-image numpy")
        print("跳过帧处理。请安装必要的库: pip install opencv-python-headless scikit-image numpy")
        return

    base_dir = config.IMAGE_OUTPUT_DIR
    if not os.path.isdir(base_dir):
        logging.error(f"帧目录 '{base_dir}' 不存在。跳过帧处理。")
        return
        
    logging.info(f"--- 步骤 8: 开始处理和筛选帧 ---")
    for dir_name in os.listdir(base_dir):
        full_path = os.path.join(base_dir, dir_name)
        if os.path.isdir(full_path):
            _process_single_directory(full_path)
    logging.info("--- 图像处理和筛选完成 ---")
