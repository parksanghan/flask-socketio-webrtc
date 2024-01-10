from flask import Flask, render_template, request, session
from flask_socketio import SocketIO, emit, join_room
import platform

app = Flask(__name__)
app.config['SECRET_KEY'] = "wubba lubba dub dub"

socketio = SocketIO(app,cors_allowed_origins= "*")
socketio.init_app(
    app,
    cors_allowed_origins="*",
    logger=True,  # 로거 활성화
    engineio_logger=True,  # 엔진 IO 로거 활성화
    admin_sid="admin",  # 관리자 인증을 위한 sid
    admin_password="admin"  # 관리자 인증을 위한 비밀번호
)
#사용자가 저장될 변수 
users_in_room = {}

#방이 저장될 변수
rooms_sid = {}

#사람의 이름 저장될 변수 
names_sid = {}


@app.route("/join", methods=["GET"])
def join():
    display_name = request.args.get('display_name')  # 영상통화를 사용하는 사용자
    mute_audio = request.args.get('mute_audio') # 1 or 0  오디오 음소거할지 안할지
    mute_video = request.args.get('mute_video') # 1 or 0  영상 음소거 할지 안할지
    room_id = request.args.get('room_id')
    session[room_id] = {"name": display_name,  # 세션은 룸 아이디를 키 값으로 가짐
                        "mute_audio": mute_audio, "mute_video": mute_video}
    return render_template("join.html", room_id=room_id, display_name=session[room_id]["name"], mute_audio=session[room_id]["mute_audio"], mute_video=session[room_id]["mute_video"])
# join.html 렌더링

@socketio.on("connect")
def on_connect():
    sid = request.sid
    print("New socket connected ", sid)


@socketio.on("join-room")
def on_join_room(data):
    sid = request.sid
    room_id = data["room_id"]
    display_name = session[room_id]["name"]

    # register sid to the room
    join_room(room_id)
    rooms_sid[sid] = room_id
    names_sid[sid] = display_name

    # broadcast to others in the room
    print("[{}] New member joined: {}<{}>".format(room_id, display_name, sid))
    emit("user-connect", {"sid": sid, "name": display_name},
         broadcast=True, include_self=False, room=room_id)

    # add to user list maintained on server
    if room_id not in users_in_room:
        users_in_room[room_id] = [sid]
        emit("user-list", {"my_id": sid})  # send own id only
    else:
        usrlist = {u_id: names_sid[u_id]
                   for u_id in users_in_room[room_id]}
        # send list of existing users to the new member
        emit("user-list", {"list": usrlist, "my_id": sid})
        # add new member to user list maintained on server
        users_in_room[room_id].append(sid)

    print("\nusers: ", users_in_room, "\n")


@socketio.on("disconnect")
def on_disconnect():
    sid = request.sid
    room_id = rooms_sid[sid]
    display_name = names_sid[sid]

    print("[{}] Member left: {}<{}>".format(room_id, display_name, sid))
    emit("user-disconnect", {"sid": sid},
         broadcast=True, include_self=False, room=room_id)

    users_in_room[room_id].remove(sid)
    if len(users_in_room[room_id]) == 0:
        users_in_room.pop(room_id)

    rooms_sid.pop(sid)
    names_sid.pop(sid)

    print("\nusers: ", users_in_room, "\n")


@socketio.on("data")
def on_data(data):
    sender_sid = data['sender_id']
    target_sid = data['target_id']
    if sender_sid != request.sid:
        print("[Not supposed to happen!] request.sid and sender_id don't match!!!")

    if data["type"] != "new-ice-candidate":
        print('{} message from {} to {}'.format(
            data["type"], sender_sid, target_sid))
    socketio.emit('data', data, room=target_sid)


if any(platform.win32_ver()):
     socketio.init_app(app, cors_allowed_origins="*")
     socketio.run(app, debug=True)