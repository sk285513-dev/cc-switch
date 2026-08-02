import asyncio, edge_tts
async def text_to_speech(text, output_file='output.mp3'):
    communicate = edge_tts.Communicate(text, 'zh-TW-XiaoxiaoNeural')
    await communicate.save(output_file)