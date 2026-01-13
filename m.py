from grpc import StatusCode
from t_tech.invest import Client, RequestError


def get_sandbox_accounts(token: str):
    with Client(token) as client:
        sb_accounts = client.sandbox.get_sandbox_accounts().accounts
        if len(sb_accounts) == 0:
            client.sandbox.open_sandbox_account()
        return client.sandbox.get_sandbox_accounts().accounts


def get_accounts(token: str):
    with Client(token) as client:
        try:
            return client.users.get_accounts().accounts
        except RequestError as e:
            if e.code == StatusCode.UNAUTHENTICATED:
                return get_sandbox_accounts(token)


def get_env_value(key: str) -> str | None:
    env_path = ".env"
    try:
        with open(env_path, "r") as f:
            for line in f:
                if line.strip().upper().startswith(f"{key.upper()}="):
                    return line.strip().split("=", 1)[1]
    except FileNotFoundError:
        pass
    return None


def update_env_file(key: str, value: str):
    env_path = ".env"
    lines = []
    key_found = False
    try:
        with open(env_path, "r") as f:
            lines = f.readlines()
    except FileNotFoundError:
        pass

    new_lines = []
    for line in lines:
        if line.strip().upper().startswith(f"{key.upper()}="):
            new_lines.append(f"{key}={value}\n")
            key_found = True
        else:
            new_lines.append(line)

    if not key_found:
        if lines and lines[-1][-1] != "\n":
            new_lines.append("\n")
        new_lines.append(f"{key}={value}\n")

    with open(env_path, "w") as f:
        f.writelines(new_lines)


if __name__ == "__main__":
    token = get_env_value("TOKEN")
    if not token:
        print("\nВведите токен Тинькофф:")
        token = input().strip()
        if not token:
            print("Токен не может быть пустым!")
            exit(1)
        update_env_file("TOKEN", token)
        print("Токен сохранен")

    accounts = get_accounts(token)
    broker_accounts = [(i, acc) for i, acc in enumerate(accounts) if acc.type == 1]

    print("\nДоступные брокерские счета ( номер, название ):")
    for idx, (_, acc) in enumerate(broker_accounts):
        print(f"  [Номер {idx + 1}] {acc.name} (id: {acc.id})")

    print("\nВведите номер аккаунта:")
    choice = int(input()) - 1

    if choice < 0 or choice >= len(broker_accounts):
        print("Неверный номер!")
        exit(1)

    selected_account = broker_accounts[choice][1]
    update_env_file("ACCOUNT_ID", selected_account.id)
    print(f"Аккаунт {selected_account.id} сохранен")

    print("\nВведите пароль для сайта:")
    password = input()
    update_env_file("PASSWORD", password)
    print("Пароль сохранен")
