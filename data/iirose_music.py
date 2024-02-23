import time
import random
import asyncio
import requests
import threading

from collections import defaultdict
from API.api_iirose import APIIirose, PlatformType
from API.api_message import at_user
from API.decorator.command import on_command, MessageType


API = APIIirose()
wait_user = {}
music_hot = True
play_list_song = []
play_playlist = False
play_playlist_time_sleep = [False, '']
now_play_song = []
skip_list_song = []
sleep_play_list = []
com_head = ">"
play_model = True
play_model_re = False


async def music_offset(Message, music_name, offset):
    global wait_user
    if offset == 1:
        m_offset = 0
    else:
        m_offset = (offset - 1) * 10
    request = requests.get(
        f'https://xc.null.red:8043/api/netease/cloudsearch?keywords={music_name}&limit=10&type=1&offset={m_offset}').json()

    if request['code'] == 200:
        msg = ''
        song_list = {}
        num = 0
        for song_data in request['result']['songs']:
            num += 1
            auther = ''
            for ar in song_data['ar']:
                auther += ar['name'] + '/'
            msg += f'{num}.{song_data["name"]} by: {auther[:-1]} \n'
            song_list[num] = song_data['id']
        msg += f'发送左侧序号播放对应歌曲或发送 退出 退出点歌\n发送 下一页/上一页 切换到下一页或上一页 当前页数：第{offset}页'
        wait_user[Message.user_id] = [song_list, offset, music_name, 'music']
    else:
        if Message.user_id in wait_user:
            del wait_user[Message.user_id]
        msg = '错误，获取数据失败，已退出选择'

    await API.send_msg(Message, at_user(Message.user_name) + "\n" + msg)


async def playlist_offset(Message, music_list_name, offset, search_type="1000"):
    global wait_user
    if offset == 1:
        m_offset = f"&offset=0"
    else:
        m_offset = f"&offset={(offset - 1) * 10}"
    request = requests.get(f'https://xc.null.red:8043/api/netease/cloudsearch?keywords={music_list_name}&limit=10&type={search_type}{m_offset}').json()

    if request['code'] == 200:
        msg = ''
        playlist = {}
        num = 0
        if str(search_type) == "10":
            request_data = request['result']["albums"]
        elif str(search_type) == "100":
            request_data = request['result']["artists"]
        else:
            request_data = request['result']['playlists']
        for playlist_data in request_data:
            num += 1
            if str(search_type) in ["10", "100"]:
                msg += f'{num}.{playlist_data["name"]}\n'
            else:
                msg += f'{num}.{playlist_data["name"]} 共{playlist_data["trackCount"]}首 by: {playlist_data["creator"]["nickname"]} \n'
            playlist[num] = playlist_data['id']
        if str(search_type) == "10":
            msg += f'发送左侧序号播放对应专辑或发送 退出 退出搜索\n发送 下一页/上一页 切换到下一页或上一页 当前页数：第{offset}页'
        elif str(search_type) == "100":
            msg += f'发送左侧序号播放对应歌手或发送 退出 退出搜索\n发送 下一页/上一页 切换到下一页或上一页 当前页数：第{offset}页'
        else:
            msg += f'发送左侧序号播放对应歌单或发送 退出 退出搜索\n发送 下一页/上一页 切换到下一页或上一页 当前页数：第{offset}页'

        if str(search_type) == "10":
            wait_user[Message.user_id] = [playlist, offset, music_list_name, 'album']
        elif str(search_type) == "100":
            wait_user[Message.user_id] = [playlist, offset, music_list_name, 'artists']
        else:
            wait_user[Message.user_id] = [playlist, offset, music_list_name, 'playlist']
    else:
        if Message.user_id in wait_user:
            del wait_user[Message.user_id]
        msg = '错误，获取数据失败，已退出选择'

    await API.send_msg(Message, at_user(Message.user_name) + "\n" + msg)


async def play_n_media(n_music_id, name_text=None):
    try:
        try:
            lrc_data = requests.get(
                f'https://xc.null.red:8043/api/netease/lyric?id={n_music_id}').json()

            if 'tlyric' in lrc_data:
                song_lrc = lrc_data['lrc']['lyric'].split('\n')
                song_lrc_t = lrc_data['tlyric']['lyric'].split('\n')

                l_lrc = {lrc.split(']')[0][1:]: lrc.split(']')[1] for lrc in song_lrc if len(lrc.split(']')) == 2}
                t_lrc = {lrc.split(']')[0][1:]: lrc.split(']')[1] for lrc in song_lrc_t if len(lrc.split(']')) == 2}

                for s_t_lrc in t_lrc:
                    try:
                        if s_t_lrc in l_lrc:
                            if t_lrc[s_t_lrc] != '':
                                l_lrc[s_t_lrc] = l_lrc[s_t_lrc] + ' | ' + t_lrc[s_t_lrc]
                    except:
                        pass

                song_lrc = '\n'.join([f'[{lrc}] {l_lrc[lrc]}' for lrc in l_lrc])
            else:
                song_lrc = lrc_data['lrc']['lyric']
        except:
            song_lrc = '[00:00.000] 歌词获取失败'

    except:
        return 'error'
    if name_text != "[电台":
        song_url = requests.get(f'https://xc.null.red:8043/meting-api/?id={n_music_id}').json()
        if song_url['url'] is None:
            return 'error'

        song_info = requests.get(f'https://xc.null.red:8043/api/netease/song/detail?ids={n_music_id}').json()['songs'][0]

        auther = ''
        for ar in song_info['ar']:
            auther += ar['name'] + '/'

        if name_text is not None:
            song_name = f'{name_text}|{song_url["level"]}] {song_info["name"]}'
        else:
            song_name = song_info["name"]

        duration = await API.play_media(True, song_url['url'], platform_type=PlatformType.netease,
                                        media_pic=song_info["al"]["picUrl"],
                                        media_name=song_name,
                                        media_auther=auther[:-1], media_lrc=song_lrc,
                                        music_song_id=song_info["id"], media_br=str(song_url['br'])[:-3])
        print(duration)
    else:
        song_info = requests.get(f'https://xc.null.red:8043/api/netease/dj/program/detail?id={n_music_id}').json()['program']

        auther = ''
        for ar in song_info['mainSong']['artists']:
            auther += ar['name'] + '/'

        song_url = requests.get(f'https://xc.null.red:8043/meting-api/?id={song_info["mainSong"]["id"]}').json()
        if song_url['url'] is None:
            return 'error'

        song_name = f'{name_text}|{song_url["level"]}] {song_info["mainSong"]["name"]}'

        duration = await API.play_media(True, song_url['url'], platform_type=PlatformType.netease,
                                        media_pic=song_info["coverUrl"],
                                        media_name=song_name,
                                        media_auther=auther[:-1], media_lrc=song_lrc,
                                        music_song_id=song_info["id"], media_br=str(song_url['br'])[:-3])

    if str(duration['code']) == '200':
        return duration['duration']
    else:
        return 'error'


@on_command(f'{com_head}点歌 ', [True, 4], command_type=[MessageType.room_chat, MessageType.private_chat])
async def music(Message, text):
    global wait_user
    request = requests.get(f'https://xc.null.red:8043/api/netease/cloudsearch?keywords={text}&limit=10&type=1').json()
    if not request['code'] == 200:
        request = requests.get(f'https://xc.null.red:8043/api/netease/search?keywords={text}&limit=10&type=1').json()
        back_url = True
    else:
        back_url = False

    if request['code'] == 200:
        msg = ''
        song_list = {}
        num = 0
        for song_data in request['result']['songs']:
            num += 1
            auther = ''
            if not back_url:
                for ar in song_data['ar']:
                    auther += ar['name'] + '/'
            else:
                for ar in song_data['artists']:
                    auther += ar['name'] + '/'
            msg += f'{num}.{song_data["name"]} by: {auther[:-1]} \n'
            song_list[num] = song_data['id']
        msg += '发送左侧序号播放对应歌曲或发送 退出 退出点歌\n发送 下一页/上一页 切换到下一页或上一页 当前页数：第1页'
        wait_user[Message.user_id] = [song_list, 1, text, 'music']
    else:
        if Message.user_id in wait_user:
            del wait_user[Message.user_id]
        msg = '错误，获取数据失败，已退出选择'

    await API.send_msg(Message, at_user(Message.user_name) + "\n" + msg)


@on_command(f'{com_head}点歌id ', [True, 6], command_type=[MessageType.room_chat, MessageType.private_chat])
async def id_music(Message, text):
    try:
        async def play_nm(id):
            data = await play_n_media(int(id), '[单歌')
            if str(data) == 'timeout':
                await API.send_msg(Message, at_user(Message.user_name) + '内部错误，歌曲解析超时')
            if str(data) == 'error':
                await API.send_msg(Message, at_user(Message.user_name) + '致命错误，运行崩溃')
        if text.isdigit():
            await play_nm(text)
        else:
            song_id = None
            if 'id' in text:
                url_data = text.split('song?')[1]
                url_data = url_data.split('&')

                for data in url_data:
                    data = data.split('=')
                    if data[0] == 'id':
                        song_id = data[1]
                        break
            if song_id:
                await play_nm(song_id)
            else:
                await API.send_msg(Message, at_user(Message.user_name) + '错误，没有从输入的信息中找到歌曲id')
    except:
        await API.send_msg(Message, at_user(Message.user_name) + '错误，请检查输入的id是否正确以及是否混杂非数字内容')


@on_command(f'{com_head}跳过', False, command_type=[MessageType.room_chat, MessageType.private_chat])
async def stop_music(Message):
    await API.stop_media()


@on_command(f'{com_head}跳过 列表', False, command_type=[MessageType.room_chat, MessageType.private_chat])
async def stop_list_music(Message):
    global play_playlist
    global skip_list_song
    global now_play_song
    global play_list_song

    await API.stop_media()
    if play_list_song:
        play_playlist = False
        if now_play_song is not [] and now_play_song[0] not in skip_list_song:
            skip_list_song.append(now_play_song[0])


@on_command(f'{com_head}清空', False, command_type=[MessageType.room_chat, MessageType.private_chat])
async def clear_music(Message):
    global play_list_song
    play_list_song = []
    await API.send_msg(Message, at_user(Message.user_name) + '已清空当前列表！')


@on_command(f'{com_head}列表', False, command_type=[MessageType.room_chat, MessageType.private_chat])
async def list_music(Message):
    global play_list_song

    if not play_list_song:
        await API.send_msg(Message, "当前队列中暂无歌曲")
        return

    result = defaultdict(dict)

    for item in play_list_song:
        category = item[3]
        name = item[4]
        result[category][name] = result[category].get(name, 0) + 1

    msg = ""

    for category, items in result.items():
        msg += f"{category}：\n"
        for count, (name, quantity) in enumerate(items.items(), 1):
            msg += f"  - {name} - 剩余 {quantity} 首\n"

    await API.send_msg(Message, at_user(Message.user_name) + "\n" + msg[:-1])


@on_command(f'{com_head}列表 ', [True, 4], command_type=[MessageType.room_chat, MessageType.private_chat])
async def music_list_skip(Message, text):
    global play_list_song

    list_text = text.split(' ')
    if list_text[0] == '删除':
        text = text[3:]
        contains_station = any(text in item[4] for item in play_list_song)
        if contains_station:
            play_list_song = [item for item in play_list_song if item[4] != text]
            await API.send_msg(Message, f'已删除 {text}！')
        else:
            await API.send_msg(Message, f'未找到包含 {text} 的媒体')
    else:
        await API.send_msg(Message, at_user(Message.user_name) + 'Error，未知指令')


@on_command(f'{com_head}歌单 ', [True, 4], command_type=[MessageType.room_chat, MessageType.private_chat])
async def music_list(Message, text):
    global play_list_song

    list_text = text.split(' ')
    if list_text[0] == '搜索':
        music_list_name = text[3:]
        request = requests.get(f'https://xc.null.red:8043/api/netease/cloudsearch?keywords={music_list_name}&limit=10&type=1000').json()

        if request['code'] == 200:
            msg = ''
            playlist = {}
            num = 0
            for playlist_data in request['result']['playlists']:
                num += 1
                msg += f'{num}.{playlist_data["name"]} 共{playlist_data["trackCount"]}首 by: {playlist_data["creator"]["nickname"]} \n'
                playlist[num] = playlist_data['id']
            msg += f'发送左侧序号播放对应歌单或发送 退出 退出搜索\n发送 下一页/上一页 切换到下一页或上一页 当前页数：第1页'
            wait_user[Message.user_id] = [playlist, 1, music_list_name, 'playlist']
        else:
            if Message.user_id in wait_user:
                del wait_user[Message.user_id]
            msg = '错误，获取数据失败，已退出选择'

        await API.send_msg(Message, at_user(Message.user_name) + "\n" + msg)
    elif list_text[0] == 'id':
        async def play_n_playlist(list_id):
            request = requests.get(f'https://xc.null.red:8043/api/netease/playlist/track/all?id={list_id}').json()
            if request['code'] == 404:
                return 404

            list_id = requests.get(f"https://xc.null.red:8043/api/netease/playlist/detail?id={list_id}").json()
            list_id = f"{list_id['playlist']['name']} by: {list_id['playlist']['creator']['nickname']}"

            for song_data in request['songs']:
                auther = ''
                for ar in song_data['ar']:
                    auther += ar['name'] + '/'
                play_list_song.append([song_data["id"], song_data['name'], auther[:-1], '歌单', list_id])

            await API.send_msg(Message, at_user(Message.user_name) + '歌单添加完毕！')
        playlist_id = None
        if 'id' in text[3:]:
            url_data = text.split('playlist?')[1]
            url_data = url_data.split('&')

            for data in url_data:
                data = data.split('=')
                if data[0] == 'id':
                    playlist_id = data[1]
                    break
        if playlist_id:
            await play_n_playlist(playlist_id)
        else:
            data = await play_n_playlist(text[3:])
            if data == 404:
                await API.send_msg(Message, at_user(Message.user_name) + '错误，未知歌单')
            elif data in [404, 200]:
                await API.send_msg(Message, at_user(Message.user_name) + '错误，没有从输入的信息中找到歌曲id')
    else:
        await API.send_msg(Message, at_user(Message.user_name) + 'Error，未知指令')


@on_command(f'{com_head}专辑 ', [True, 4], command_type=[MessageType.room_chat, MessageType.private_chat])
async def album_list(Message, text):
    global play_list_song

    list_text = text.split(' ')
    if list_text[0] == '搜索':
        music_list_name = text[3:]
        request = requests.get(f'https://xc.null.red:8043/api/netease/cloudsearch?keywords={music_list_name}&limit=10&type=10').json()

        if request['code'] == 200:
            msg = ''
            playlist = {}
            num = 0
            for playlist_data in request['result']['albums']:
                num += 1
                msg += f"{num}.{playlist_data['name']} by: {playlist_data['artist']['name']}\n"
                playlist[num] = playlist_data['id']
            msg += f'发送左侧序号播放对应专辑或发送 退出 退出搜索\n发送 下一页/上一页 切换到下一页或上一页 当前页数：第1页'
            wait_user[Message.user_id] = [playlist, 1, music_list_name, 'album']
        else:
            if Message.user_id in wait_user:
                del wait_user[Message.user_id]
            msg = '错误，获取数据失败，已退出选择'

        await API.send_msg(Message, at_user(Message.user_name) + "\n" + msg)
    elif list_text[0] == 'id':
        async def play_n_playlist(list_id):
            request = requests.get(f'https://xc.null.red:8043/api/netease/album?id={list_id}').json()
            if request['code'] == 404:
                return 404
            for song_data in request['songs']:
                auther = ''
                for ar in song_data['ar']:
                    auther += ar['name'] + '/'
                play_list_song.append([song_data["id"], song_data['name'], auther[:-1], '专辑',
                                       f"{request['album']['name']} by: {request['album']['artist']['name']}"])

            await API.send_msg(Message, at_user(Message.user_name) + '专辑添加完毕！')
        playlist_id = None
        if 'id' in text[3:]:
            url_data = text.split('album?')[1]
            url_data = url_data.split('&')

            for data in url_data:
                data = data.split('=')
                if data[0] == 'id':
                    playlist_id = data[1]
                    break
        if playlist_id:
            await play_n_playlist(playlist_id)
        else:
            data = await play_n_playlist(text[3:])
            if data == 404:
                await API.send_msg(Message, at_user(Message.user_name) + '错误，未知专辑')
            elif data in [404, 200]:
                await API.send_msg(Message, at_user(Message.user_name) + '错误，没有从输入的信息中找到专辑id')
    else:
        await API.send_msg(Message, at_user(Message.user_name) + 'Error，未知指令')


@on_command(f'{com_head}电台 ', [True, 4], command_type=[MessageType.room_chat, MessageType.private_chat])
async def radio_list(Message, text):
    global play_list_song

    list_text = text.split(' ')
    if list_text[0] == '搜索':
        music_list_name = text[3:]
        request = requests.get(f'https://xc.null.red:8043/api/netease/cloudsearch?keywords={music_list_name}&limit=10&type=1009').json()

        if request['code'] == 200:
            msg = ''
            playlist = {}
            num = 0
            for playlist_data in request['result']['djRadios']:
                num += 1
                list_id = requests.get("https://xc.null.red:8043/api/netease/dj/detail?rid=" + playlist_data['id']).json()
                msg += f"{list_id['data']['name']} by: {list_id['data']['dj']['nickname']}\n"
                playlist[num] = playlist_data['id']
            msg += f'注：电台有音频解析失败的可能，未必所有音频可播放\n发送左侧序号播放对应电台或发送 退出 退出搜索'
            wait_user[Message.user_id] = [playlist, 1, music_list_name, 'radio']
        else:
            if Message.user_id in wait_user:
                del wait_user[Message.user_id]
            msg = '错误，获取数据失败，已退出选择'

        await API.send_msg(Message, at_user(Message.user_name) + "\n" + msg)
    elif list_text[0] == 'id':
        async def play_n_playlist(list_id):
            request = requests.get(f'https://xc.null.red:8043/api/netease/dj/program?rid={list_id}').json()
            if request['code'] == 404:
                return 404

            list_id = requests.get(f"https://xc.null.red:8043/api/netease/dj/detail?rid={list_id}").json()
            list_id = f"{list_id['data']['name']} by: {list_id['data']['dj']['nickname']}"

            for song_data in request['programs']:
                auther = ''
                song_id = song_data['id']
                song_data = song_data['mainSong']
                for ar in song_data['artists']:
                    auther += ar['name'] + '/'
                play_list_song.append([song_id, song_data['name'], auther[:-1], '电台', list_id])

            await API.send_msg(Message, at_user(Message.user_name) + '电台添加完毕！')
        playlist_id = None
        if 'id' in text[3:]:
            url_data = text.split('radio?')[1]
            url_data = url_data.split('&')

            for data in url_data:
                data = data.split('=')
                if data[0] == 'id':
                    playlist_id = data[1]
                    break
        if playlist_id:
            await play_n_playlist(playlist_id)
        else:
            data = await play_n_playlist(text[3:])
            if data == 404:
                await API.send_msg(Message, at_user(Message.user_name) + '错误，未知电台')
            elif data in [404, 200]:
                await API.send_msg(Message, at_user(Message.user_name) + '错误，没有从输入的信息中找到电台id')
    else:
        await API.send_msg(Message, at_user(Message.user_name) + 'Error，未知指令')


@on_command(f'{com_head}歌手 ', [True, 4], command_type=[MessageType.room_chat, MessageType.private_chat])
async def radio_list(Message, text):
    global play_list_song

    list_text = text.split(' ')
    if list_text[0] == '搜索':
        music_list_name = text[3:]
        request = requests.get(f'https://xc.null.red:8043/api/netease/cloudsearch?keywords={music_list_name}&limit=10&type=100').json()

        if request['code'] == 200:
            msg = ''
            playlist = {}
            num = 0
            for playlist_data in request['result']['artists']:
                num += 1
                msg += f"{num}.{playlist_data['name']}\n"
                playlist[num] = playlist_data['id']
            msg += f'发送左侧序号播放对应电台或发送 退出 退出搜索\n发送 下一页/上一页 切换到下一页或上一页 当前页数：第1页'
            wait_user[Message.user_id] = [playlist, 1, music_list_name, 'artists']
        else:
            if Message.user_id in wait_user:
                del wait_user[Message.user_id]
            msg = '错误，获取数据失败，已退出选择'

        await API.send_msg(Message, at_user(Message.user_name) + "\n" + msg)
    elif list_text[0] == 'id':
        async def play_n_playlist(list_id):
            request = requests.get(f"https://xc.null.red:8043/api/netease/artist/songs?id={list_id}").json()

            for song_data in request['songs']:
                auther = ''
                song_id = song_data['id']
                for ar in song_data['ar']:
                    auther += ar['name'] + '/'
                play_list_song.append([song_id, song_data['name'], auther[:-1], '歌手', list_id])

            await API.send_msg(Message, at_user(Message.user_name) + '该歌手作品已添加完毕！')
        playlist_id = None
        if 'id' in text[3:]:
            url_data = text.split('artist?')[1]
            url_data = url_data.split('&')

            for data in url_data:
                data = data.split('=')
                if data[0] == 'id':
                    playlist_id = data[1]
                    break
        if playlist_id:
            await play_n_playlist(playlist_id)
        else:
            data = await play_n_playlist(text[3:])
            if data == 404:
                await API.send_msg(Message, at_user(Message.user_name) + '错误，未知歌手')
            elif data in [404, 200]:
                await API.send_msg(Message, at_user(Message.user_name) + '错误，没有从输入的信息中找到歌手id')
    else:
        await API.send_msg(Message, at_user(Message.user_name) + 'Error，未知指令')


@on_command('<TT1', False, command_type=[MessageType.room_chat, MessageType.private_chat])
async def t_1(Message):
    global music_hot
    if music_hot:
        music_hot = False
    else:
        music_hot = True
    await API.send_msg(Message, str(music_hot))


@on_command(f'{com_head}模式', False, command_type=[MessageType.room_chat, MessageType.private_chat])
async def model_stats(Message):
    global play_model
    global play_model_re

    if play_model:
        model_text = '顺序'
    else:
        model_text = '随机'

    if play_model_re:
        re_text = '是'
    else:
        re_text = '否'

    await API.send_msg(Message, f"当前状态：\n播放模式：{model_text} 循环播放：{re_text}")


@on_command(f'{com_head}模式 ', [True, 4], command_type=[MessageType.room_chat, MessageType.private_chat])
async def model_gh(Message, text):
    global play_model
    global play_model_re

    if text[:2] == '列表':
        if play_model:
            play_model = False
        else:
            play_model = True
    elif text[:2] == '循环':
        if play_model_re:
            play_model_re = False
        else:
            play_model_re = True

    if play_model:
        model_text = '顺序'
    else:
        model_text = '随机'

    if play_model_re:
        re_text = '是'
    else:
        re_text = '否'

    await API.send_msg(Message, f"当前状态：\n播放模式：{model_text} 循环播放：{re_text}")


@on_command(f'{com_head}帮助', False, command_type=[MessageType.room_chat, MessageType.private_chat])
async def music_help(Message):
    menu = (f'{com_head}点歌 (歌名) - 搜索网易云歌曲，可解析VIP歌曲\n'
            f'{com_head}点歌id (歌曲id) - 按id播放网易云歌曲\n'
            f'{com_head}列表 - 查看在列表中的歌\n'
            f'{com_head}列表 删除 (歌单/专辑/电台 名) - 删除在列表中包含指定 歌单/专辑/电台 名的歌曲\n'
            f'{com_head}跳过 - 跳过当前机器人播放的歌曲\n'
            f'{com_head}跳过 列表 - 跳过当前队列中的歌曲\n'
            f'{com_head}清空 - 清空队列中的所有歌曲\n'
            f'{com_head}歌单 搜索 (歌单名) - 搜索网易云歌单\n'
            f'{com_head}歌单 id (歌单id) - 用歌单id播放歌单\n'
            f'{com_head}专辑 搜索 (专辑名) - 搜索网易云专辑\n'
            f'{com_head}专辑 id (专辑id) - 用歌单id播放专辑\n'
            f'{com_head}电台 搜索 (电台名) - 搜索网易云电台\n'
            f'{com_head}电台 id (电台id) - 用歌单id播放电台\n'
            f'{com_head}歌手 搜索 (歌手名) - 搜索网易云歌手\n'
            f'{com_head}歌手 id (歌手id) - 用歌手id播放歌手所有歌曲\n'
            f'{com_head}模式 - 查询当前模式状态\n'
            f'{com_head}模式 列表/循环 - 更改 列表/循环 的状态\n'
            f'PS：左侧的 {com_head} 为指令头，() 中包裹的内容为参数')

    await API.send_msg(Message, at_user(Message.user_name) + "\n" + menu)


async def room_message(Message):
    global wait_user
    global play_list_song
    if Message.user_id in wait_user:
        if Message.message[:1] == com_head:
            return
        if Message.message == '上一页':
            if wait_user[Message.user_id][-1] == 'music':
                if wait_user[Message.user_id][1] != 1:
                    wait_user[Message.user_id][1] -= 1
                await music_offset(Message, wait_user[Message.user_id][2], wait_user[Message.user_id][1])
            elif wait_user[Message.user_id][-1] == 'playlist':
                if wait_user[Message.user_id][1] != 1:
                    wait_user[Message.user_id][1] -= 1
                await playlist_offset(Message, wait_user[Message.user_id][2], wait_user[Message.user_id][1])
            elif wait_user[Message.user_id][-1] == 'album':
                if wait_user[Message.user_id][1] != 1:
                    wait_user[Message.user_id][1] -= 1
                await playlist_offset(Message, wait_user[Message.user_id][2], wait_user[Message.user_id][1], "10")
            elif wait_user[Message.user_id][-1] == 'artists':
                if wait_user[Message.user_id][1] != 1:
                    wait_user[Message.user_id][1] -= 1
                await playlist_offset(Message, wait_user[Message.user_id][2], wait_user[Message.user_id][1], "100")
            return
        if Message.message == '下一页':
            if wait_user[Message.user_id][-1] == 'music':
                wait_user[Message.user_id][1] += 1
                await music_offset(Message, wait_user[Message.user_id][2], wait_user[Message.user_id][1])
            elif wait_user[Message.user_id][-1] == 'playlist':
                wait_user[Message.user_id][1] += 1
                await playlist_offset(Message, wait_user[Message.user_id][2], wait_user[Message.user_id][1])
            elif wait_user[Message.user_id][-1] == 'album':
                wait_user[Message.user_id][1] += 1
                await playlist_offset(Message, wait_user[Message.user_id][2], wait_user[Message.user_id][1], "10")
            elif wait_user[Message.user_id][-1] == 'artists':
                wait_user[Message.user_id][1] += 1
                await playlist_offset(Message, wait_user[Message.user_id][2], wait_user[Message.user_id][1], "100")
            return
        if Message.message == '退出':
            await API.send_msg(Message, at_user(Message.user_name) + '已退出')
            del wait_user[Message.user_id]
            return
        try:
            select_num = int(Message.message)
            if not 1 <= select_num <= 10:
                await API.send_msg(Message, at_user(Message.user_name) + '错误：输入内容超出了1-10|退出请发送 退出')
                return
        except:
            await API.send_msg(Message, at_user(Message.user_name) + '错误：输入内容非1-10纯数字|退出请发送 退出')
            return

        if wait_user[Message.user_id][-1] == 'music':
            await API.send_msg(Message, at_user(Message.user_name) + '解析中...')
            song_id = wait_user[Message.user_id][0][select_num]
            del wait_user[Message.user_id]
            song_status = await play_n_media(song_id, '[单歌')
            if song_status == 'error':
                await API.send_msg(Message, at_user(Message.user_name) + '内部错误：解析失败，已退出点歌')
                del wait_user[Message.user_id]
                return
            elif song_status == 'timeout':
                await API.send_msg(Message, at_user(Message.user_name) + '内部错误：歌曲解析超时')
                del wait_user[Message.user_id]
                return
        elif wait_user[Message.user_id][3] == 'playlist':
            await API.send_msg(Message, at_user(Message.user_name) + '正在添加中...')
            playlist = wait_user[Message.user_id][0][select_num]
            del wait_user[Message.user_id]
            request = requests.get(f'https://xc.null.red:8043/api/netease/playlist/track/all?id={playlist}').json()

            list_id = requests.get(f"https://xc.null.red:8043/api/netease/playlist/detail?id={playlist}").json()
            list_id = f"{list_id['playlist']['name']} by: {list_id['playlist']['creator']['nickname']}"

            for song_data in request['songs']:
                auther = ''
                for ar in song_data['ar']:
                    auther += ar['name'] + '/'
                play_list_song.append([song_data["id"], song_data['name'], auther[:-1], '歌单', list_id])

            await API.send_msg(Message, at_user(Message.user_name) + '歌单添加完毕！')
            return
        elif wait_user[Message.user_id][3] == 'album':
            await API.send_msg(Message, at_user(Message.user_name) + '正在添加中...')
            list_id = wait_user[Message.user_id][0][select_num]
            del wait_user[Message.user_id]
            request = requests.get(f'https://xc.null.red:8043/api/netease/album?id={list_id}').json()

            for song_data in request['songs']:
                auther = ''
                for ar in song_data['ar']:
                    auther += ar['name'] + '/'
                play_list_song.append([song_data["id"], song_data['name'], auther[:-1], '专辑', f"{request['album']['name']} by: {request['album']['artist']['name']}"])

            await API.send_msg(Message, at_user(Message.user_name) + '专辑添加完毕！')
            return
        elif wait_user[Message.user_id][3] == 'radio':
            await API.send_msg(Message, at_user(Message.user_name) + '正在添加中...')
            list_id = wait_user[Message.user_id][0][select_num]
            del wait_user[Message.user_id]
            request = requests.get(f'https://xc.null.red:8043/api/netease/dj/program?rid={list_id}').json()

            list_id = requests.get(f"https://xc.null.red:8043/api/netease/dj/detail?rid={list_id}").json()
            list_id = f"{list_id['data']['name']} by: {list_id['data']['dj']['nickname']}"

            for song_data in request['programs']:
                auther = ''
                song_id = song_data['id']
                song_data = song_data['mainSong']
                for ar in song_data['artists']:
                    auther += ar['name'] + '/'
                play_list_song.append([song_id, song_data['name'], auther[:-1], '电台', list_id])

            await API.send_msg(Message, at_user(Message.user_name) + '电台添加完毕！')
            return
        elif wait_user[Message.user_id][3] == 'artists':
            await API.send_msg(Message, at_user(Message.user_name) + '正在添加中...')
            list_id = wait_user[Message.user_id][0][select_num]
            del wait_user[Message.user_id]
            request = requests.get(f"https://xc.null.red:8043/api/netease/artist/songs?id={list_id}").json()

            for song_data in request['artists']:
                auther = ''
                song_id = song_data['id']
                for ar in song_data['ar']:
                    auther += ar['name'] + '/'
                play_list_song.append([song_id, song_data['name'], auther[:-1], '歌手', list_id])

            await API.send_msg(Message, at_user(Message.user_name) + '该歌手作品已添加完毕！')
            return
        try:
            del wait_user[Message.user_id]
        except:
            pass


async def media_message(Message):
    global music_hot
    global play_playlist_time_sleep
    text = Message.media_url.split('?id=')
    if len(text) >= 2:
        if str(text[1]) == str(play_playlist_time_sleep[1]):
            play_playlist_time_sleep[0] = True

        def hot_comments():
            if not music_hot:
                return
            request = requests.get(
                f'https://xc.null.red:8043/api/netease/comment/music?id={text[1]}&limit=1').json()
            if request['code'] == 200:
                try:
                    msg = random.choice(request['hotComments'])
                    asyncio.run(API.send_msg_to_room(
                        f'\\\\\\*\n### 网易云热评：\n**{msg["content"]}**  ——**{msg["user"]["nickname"]}** *({msg["timeStr"]})*'))
                except:
                    pass

        threading.Thread(target=hot_comments).start()


def play_playlist_song():
    global play_list_song
    global now_play_song
    global play_playlist
    global skip_list_song
    global sleep_play_list
    global play_playlist_time_sleep
    global play_model
    global play_model_re

    while True:
        try:
            if play_playlist:
                continue

            if play_list_song:
                play_playlist = True

                if play_model_re:
                    if play_model:
                        play_song = play_list_song.pop(0)
                        play_list_song.append(play_song)
                    else:
                        play_song = random.choice(play_list_song)
                else:
                    if play_model:
                        play_song = play_list_song.pop(0)
                    else:
                        play_song = random.choice(play_list_song)
                        play_list_song.remove(play_song)

                now_play_song = play_song
                play_playlist_time_sleep[1] = str(play_song[0])
                song_time = asyncio.run(play_n_media(play_song[0], f'[{play_song[3]}'))
                if song_time in ['timeout', 'error', 0]:
                    continue

                sleep_play_list = [song_time, play_song[0]]
        except:
            pass


def sleep_play():
    global play_playlist
    global skip_list_song
    global play_playlist_time_sleep
    global sleep_play_list

    while True:
        try:
            if not sleep_play_list:
                continue
            while True:
                if play_playlist_time_sleep[0]:
                    play_playlist_time_sleep[0] = False
                    time.sleep(sleep_play_list[0])

                    if not sleep_play_list[1] in skip_list_song:
                        play_playlist = False
                    else:
                        del skip_list_song[sleep_play_list[1]]
                    sleep_play_list = []
                    break
        except:
            pass


async def on_init():
    threading.Thread(target=play_playlist_song).start()
    threading.Thread(target=sleep_play).start()
