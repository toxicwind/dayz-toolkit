from dayz_discord_ops.config import env_bool

def test_env_bool_defaults():
    assert env_bool('NO_SUCH_VAR', False) is False
