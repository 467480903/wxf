import argparse
import os
from pydub import AudioSegment


def mp3_to_wav(mp3_path: str, wav_path: str = None, sample_rate: int = 16000, channels: int = 1) -> str:
    """将MP3格式文件转换为WAV格式文件。

    Args:
        mp3_path: 输入的MP3文件路径
        wav_path: 输出的WAV文件路径，默认与输入同目录，扩展名改为.wav
        sample_rate: 采样率，默认16000Hz
        channels: 声道数，默认1（单声道）

    Returns:
        输出的WAV文件路径
    """
    if not os.path.isfile(mp3_path):
        raise FileNotFoundError(f"MP3文件不存在: {mp3_path}")

    if wav_path is None:
        wav_path = os.path.splitext(mp3_path)[0] + ".wav"

    audio = AudioSegment.from_mp3(mp3_path)
    audio = audio.set_frame_rate(sample_rate).set_channels(channels)
    audio.export(wav_path, format="wav")

    print(f"转换完成: {mp3_path} -> {wav_path}")
    return wav_path


def main():
    parser = argparse.ArgumentParser(description="将MP3格式文件转换为WAV格式文件")
    parser.add_argument("mp3_path", help="输入的MP3文件路径")
    parser.add_argument("-o", "--output", default=None, help="输出的WAV文件路径（默认与输入同目录）")
    parser.add_argument("-r", "--sample-rate", type=int, default=16000, help="采样率，默认16000Hz")
    parser.add_argument("-c", "--channels", type=int, default=1, choices=[1, 2], help="声道数，默认1（单声道）")
    args = parser.parse_args()

    mp3_to_wav(args.mp3_path, args.output, args.sample_rate, args.channels)


if __name__ == "__main__":
    main()
