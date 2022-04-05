import matplotlib.pyplot as plt
import socket
import json


HOST = "127.0.0.1"
PORT = 47777


def serve():
    keys = set()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        while True:
            try:
                conn, addr = s.accept()
                with conn:
                    while True:
                        data = conn.recv(1024)
                        if not data:
                            break
                        x = json.loads(data.decode('utf8').strip())
                        leader = x['leader']
                        values = x['commit']
                        new_keys = values.keys()
                        if new_keys != keys:
                            plt.clf()
                            keys = set(new_keys)
                        names = [i[5:11] for i in values.keys()]
                        colors = ['grey'] * len(names)
                        # colors[list(values.keys()).index(leader)] = 'blue'
                        idx = list(values.values())

                        plt.bar(names, idx, color=colors)
                        plt.pause(0.5)
                        plt.draw()
            except Exception as e:
                print(e)
                continue


if __name__ == '__main__':
    plt.show()
    serve()
