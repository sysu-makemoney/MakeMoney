# -- coding:UTF-8 --
from flask import render_template, redirect, url_for, request, json
from flask_login import current_user,login_user,logout_user, login_required
from app import app,db
from app.models import Template,Answer
from app.models import User,Task,Receiver,receivers
from app.utils.trans import UserToJson, TaskToJson

json_true = json.dumps('succeed')
json_false = json.dumps('failed')
'''
发布任务（需登录）
接收新建任务的所有需求信息，以当前登录user进行发布
'''
@app.route('/task/sponsor', methods=['POST'])
@login_required
def sponsor_task():
    print(request.method)
    if request.method == 'POST':
        #获得post来的task数据
        json_data = json.loads(request.data)
        if 'title' not in json_data:
            return json.dumps({'errmsg': '没有传递title'})
        task = Task(
            title = json_data['title'],
            sponsor = current_user,
            type = json_data['type'] if 'type' in json_data else '问卷',
            # start_time = json_data['start_time'] if 'start_time' in json_data else None,
            # end_time = json_data['end_time'] if 'end_time' in json_data else None,
            pay = json_data['pay'] if 'pay' in json_data else 0,
            detail = json_data['detail'] if 'detail' in json_data else None,
            receiver_limit = json_data['receiver_limit'] if 'receiver_limit' in json_data else 1,
            received_number = json_data['received_number'] if 'received_number' in json_data else 0,
            extra_content = json_data['extra_content'] if 'extra_content' in json_data else None,
            state = 0,
            images = json_data['images'] if 'images'in json_data else None
            )

        task.template = Template()
        task.template.questions = json_data['questions'] if 'questions' in json_data else []
        task.template.options = json_data['options'] if 'options' in json_data else []
        task.template.types = json_data['types'] if 'types' in json_data else []
        
        db.session.add(task)
        db.session.commit()

        return json.dumps(task.id)

    return json.dumps({'errmsg': '没有使用POST请求'})

'''
接受任务(需登录）
接收任务的task_id，以当前user进行接收
'''
@app.route('/task/receive', methods=['POST'])
@login_required
def receive_task():
    if request.method == 'POST':
        #获得POST来的task id
        json_data = json.loads(request.data)
        if 'task_id' not in json_data:
            return json.dumps({'errmsg': '没有传递task_id'})
        task = Task.query.filter_by(id=json_data['task_id']).first()

        #如果没有这个任务则返回错误
        if task==None :
            return json.dumps({'errmsg': '没有该task_id的任务'})
        print(len(task.receivers))

        #判断人数限制是否已经达到
        if task.receiver_limit <= len(task.receivers):
            print('receiver limit!')
            return json.dumps({'errmsg': '任务接收人数已满'})

        #判断是否重复接收任务
        for re in task.receivers:
            if re.uid == current_user.id:
                print('user had receivered this task!')
                return json.dumps({'errmsg': '用户已经接收了该任务'})

        #当满足条件，新建一个receiver
        # receiver = Receiver.query.filter_by(id=current_user.id).first()
        # if(receiver==None):
        receiver = Receiver(tid = json_data['task_id'], uid = current_user.id)

        #接收任务
        task.receivers.append(receiver)
        task.received_number += 1
        task.state = 1
        print(task.receivers)

        db.session.add(receiver)
        db.session.commit()

        return json_true
    return json.dumps({'errmsg': '没有使用POST请求'})


'''
用户提交问卷答案 需要'user_id' 'task_id' 'answers'
'''
@app.route('/summit/answer', methods=['POST'])
def summit_answer():
    if request.method == 'POST':
        json_data = json.loads(request.data)
        if 'task_id' in json_data:
            if 'user_id' in json_data:
                if 'answers' in json_data:
                    rec = Receiver.query.filter_by(uid=json_data['user_id'], tid=json_data['task_id']).first()
                    if rec==None:
                        return json.dumps({'errmsg': '没有这个任务或者该用户没有接受该任务'})
                    rec.answers.answers = json_data['answers']
                    rec.finished = True
                    task = Task.query.filter_by(id=json_data['task_id']).first()
                    task.finished_number = task.finished_number+1
                    db.session.commit()
                    return json_true
            return json.dumps({'errmsg': '没有传递user_id'})
        return json.dumps({'errmsg': '没有传递task_id'})
    return json.dumps({'errmsg': '没有使用POST请求'})



'''
退出任务
接收 'user_id' 和 'task_id'
'''
@app.route('/task_quit', methods=['POST'])
def task_quit():
    if request.method == 'POST':
        json_data = json.loads(request.data)
        if 'task_id' in json_data:
            if 'user_id' in json_data:
                task = Task.query.filter_by(id=json_data['task_id']).first()
                rec = Receiver.query.filter_by(uid=json_data['user_id'], tid=json_data['task_id']).first()
                if (task==None or rec==None):
                    return json.dumps({'errmsg': '用户id或任务id错误'})
                task.received_number -= 1
                for current_rec in task.receivers:
                    if current_rec.uid == rec.uid:
                        task.receivers.remove(current_rec)
                        print('succeed')

                receiver = Receiver.query.filter_by(uid=json_data['user_id'], tid=json_data['task_id']).first()
                db.session.delete(receiver)
                db.session.commit()
                return json_true

            return json.dumps({'errmsg': '没有传递user_id'})
        return json.dumps({'errmsg': '没有传递task_id'})
    return json.dumps({'errmsg': '没有使用POST请求'})


'''
撤销任务
接收 'user_id' 和 'task_id'
'''
@app.route('/task_cancel', methods=['POST'])
def task_cancel():
    if request.method == 'POST':
        json_data = json.loads(request.data)
        if 'task_id' in json_data:
            if 'user_id' in json_data:
                task = Task.query.filter_by(id=json_data['task_id']).first()
                #判断task id是否正确
                if task==None:
                    return json.dumps({'errmsg': '任务id错误，无该任务'})
                #判断是否是当前用户
                if task.sponsor.id != json_data['user_id']:
                    return json.dumps({'errmsg': '该用户不是任务发起者'})

                receivers = Receiver.query.filter_by(tid=json_data['task_id']).all()
                for rec in receivers:
                    db.session.delete(rec)
                task = Task.query.filter_by(id=json_data['task_id']).first()
                db.session.delete(task)
                db.session.commit()
                return json_true
            return json.dumps({'errmsg': '没有传递user_id'})
        return json.dumps({'errmsg': '没有传递task_id'})
    return json.dumps({'errmsg': '没有使用POST请求'})
