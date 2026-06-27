from offset_move_common import run_offset

if __name__ == "__main__":
    run_offset(offset_l=(0.02, 0, 0), offset_r=(0.01,0,0))
    # run_offset(offset_l=(0, 0.02*5, 0), offset_r=(0, -0.02*5,0))#外
    run_offset(offset_l=(0, -0.02*4, 0), offset_r=(0, 0.02*4,0))#内