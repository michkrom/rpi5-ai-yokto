# yokto SWU generation include
# This provides the common SWU generation code

inherit swupdate

# No image dependency declared - we find the file after build
IMAGE_DEPENDS = ""

python do_swuimage () {
    import os
    import shutil
    import bz2
    import gzip
    import glob
    import hashlib
    import time
    
    list_for_cpio = ["sw-description"]
    s = d.getVar('S')
    imgdeploydir = d.getVar('SWUDEPLOYDIR')
    deploydir = d.getVar('DEPLOY_DIR_IMAGE')
    swu_pattern = d.getVar('SWU_IMAGE_PATTERN')
    
    # Find image matching pattern (should be .wic.bz2)
    matches = glob.glob(os.path.join(deploydir, swu_pattern))
    if not matches:
        bb.fatal(f"Could not find {swu_pattern} in {deploydir}")
    
    wic_bz2 = matches[-1]
    wic_gz_name = "image.wic.gz"
    
    # Calculate hash from the bz2 file
    with open(wic_bz2, 'rb') as f:
        bz2_data = f.read()
        hash_value = hashlib.sha256(bz2_data).hexdigest()[:16]
    
    # Decompress bz2 and recompress as gzip (SWUpdate needs zlib/gzip)
    decompressed = bz2.decompress(bz2_data)
    with gzip.open(os.path.join(s, wic_gz_name), 'wb') as f_out:
        f_out.write(decompressed)
    
    # Generate sw-description with compressed flag (SWUpdate libconfig format)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    sw_desc = f'''software = {{
    version = "{timestamp}";
    files-hash = "{hash_value}";
    allow-downgrade = true;
    images: {{
        image-wic: {{
            filename = "image.wic.gz";
            type = "raw";
            device = "/dev/mmcblk0";
            compressed = "zlib";
        }}
    }}
}};

'''
    with open(os.path.join(s, "sw-description"), 'w') as f:
        f.write(sw_desc)
    
    list_for_cpio.append(wic_gz_name)
    
    # Create the SWU (uncompressed cpio - SWUpdate handles decompression)
    os.chdir(s)
    updateimage = d.getVar('IMAGE_NAME') + '.swu'
    line = 'for i in ' + ' '.join(list_for_cpio) + '; do echo $i;done | cpio -ov -H crc --reproducible > ' + os.path.join(imgdeploydir, updateimage)
    os.system(line)
}