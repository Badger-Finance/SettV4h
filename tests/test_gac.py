import brownie
from brownie import (
    SettV1h, 
    SettV1_1h, 
    SettV4h, 
    interface, 
    accounts, 
    ERC20Upgradeable
)
import pytest
from badger_utils.token_utils.distribute_from_whales_realtime import (
    distribute_from_whales_realtime_percentage
)

"""
Test for integration of GAC pausing functionalities to Setts
"""

MAX_UINT256 = 2 ** 256 - 1

LIST_OF_EXPLOITERS = [
    "0xa33B95ea28542Ada32117B60E4F5B4cB7D1Fc19B",
    "0x4fbf7701b3078B5bed6F3e64dF3AE09650eE7DE5",
    "0x1B1b391D1026A4e3fB7F082ede068B25358a61F2",
    "0xEcD91D07b1b6B81d24F2a469de8e47E3fe3050fd",
    "0x691dA2826AC32BBF2a4b5d6f2A07CE07552A9A8E",
    "0x91d65D67FC573605bCb0b5E39F9ef6E18aFA1586",
    "0x0B88A083dc7b8aC2A84eBA02E4acb2e5f2d3063C",
    "0x2eF1b70F195fd0432f9C36fB2eF7C99629B0398c",
    "0xbbfD8041EbDE22A7f3e19600B4bab4925Cc97f7D",
    "0xe06eD65924dB2e7b4c83E07079A424C8a36701E5",
]

SETT_ADDRESSES_V1 = [
    "0xd04c48A53c111300aD41190D63681ed3dAd998eC",
    "0x6dEf55d2e18486B9dDfaA075bc4e4EE0B28c1545",
    "0x19D97D8fA813EE2f51aD4B4e04EA08bAf4DFfC28",
    "0xb9D076fDe463dbc9f915E5392F807315Bf940334",
    "0xAf5A1DECfa95BAF63E0084a35c62592B774A2A87",
    "0x235c9e24D3FB2FAFd58a2E49D454Fdcd2DBf7FF1",
]

SETT_ADDRESSES_V1_1 = [
    "0x1862A18181346EBd9EdAf800804f89190DeF24a5",
    "0x88128580ACdD9c04Ce47AFcE196875747bF2A9f6",
    "0x8a8FFec8f4A0C8c9585Da95D9D97e8Cd6de273DE",
    "0xC17078FDd324CC473F8175Dc5290fae5f2E84714",
    "0x758A43EE2BFf8230eeb784879CdcFF4828F2544D",
]

SETT_ADDRESSES_V4 = [
    "0x2B5455aac8d64C14786c3a29858E43b5945819C0",
    "0xaE96fF08771a109dc6650a1BdCa62F2d558E40af",
    "0x27E98fC7d05f54E544d16F58C194C2D7ba71e3B5",
    "0x599D92B453C010b1050d31C364f6ee17E819f193",
    "0x26B8efa69603537AC8ab55768b6740b67664D518",
    "0xfd05D3C7fe2924020620A8bE4961bBaA747e6305",
    "0x937B8E917d0F36eDEBBA8E459C5FB16F3b315551",
    "0x8c76970747afd5398e958bdfada4cf0b9fca16c4",
    "0x55912d0cf83b75c492e761932abc4db4a5cb1b17",
    "0xf349c0faa80fc1870306ac093f75934078e28991",
    "0x5dce29e92b1b939f8e8c60dcf15bde82a85be4a9",
    "0xBE08Ef12e4a553666291E9fFC24fCCFd354F2Dd2",
    "0x53c8e199eb2cb7c01543c137078a038937a68e40",
]


@pytest.mark.parametrize(
    "settAddress",
    SETT_ADDRESSES_V1 + SETT_ADDRESSES_V1_1 + SETT_ADDRESSES_V4,
)
def test_gac_pause(settAddress, proxy_admin, proxy_admin_gov, bve_cvx, bcvx_crv):

    # UPGRADE block
    if settAddress in SETT_ADDRESSES_V1:
        vault_proxy = SettV1h.at(settAddress)
        governance = accounts.at(vault_proxy.governance(), force=True)

        new_vault_logic = SettV1h.deploy({"from": governance})

    elif settAddress in SETT_ADDRESSES_V1_1:
        vault_proxy = SettV1_1h.at(settAddress)
        governance = accounts.at(vault_proxy.governance(), force=True)

        new_vault_logic = SettV1_1h.deploy({"from": governance})
    else:
        vault_proxy = SettV4h.at(settAddress)
        governance = accounts.at(vault_proxy.governance(), force=True)

        new_vault_logic = SettV4h.deploy({"from": governance})

    if bve_cvx.paused() and not settAddress == bve_cvx.address:
        bve_gov = accounts.at(bve_cvx.governance(), force=True)
        bve_cvx.unpause({"from": bve_gov})

    if bcvx_crv.paused() and not settAddress == bcvx_crv.address:
        bcvx_crv_gov = accounts.at(bcvx_crv.governance(), force=True)
        bcvx_crv.unpause({"from": bcvx_crv_gov})

    # ProxyAdmin is currently different for bslpWbtcibBTC
    if vault_proxy.address == "0x8a8FFec8f4A0C8c9585Da95D9D97e8Cd6de273DE":
        proxy_admin = interface.IProxyAdmin("0x4599F2913a3db4E73aA77A304cCC21516dd7270D")
        proxy_admin_gov = accounts.at("0x576cd258835c529b54722f84bb7d4170aa932c64", force=True)

    # Execute upgrade
    proxy_admin.upgrade(vault_proxy, new_vault_logic, {"from": proxy_admin_gov})

    ## You can unpause if GAC is paused or unpaused (SettV1 can't be paused directly)
    try:
        if vault_proxy.paused() == True:
            vault_proxy.unpause({"from": governance})
            assert vault_proxy.paused() == False
    except:
        pass

    ## GAC Pause Block

    ## Get GAC actors
    gac = interface.IGac(vault_proxy.GAC())
    gac_gov = accounts.at(gac.DEV_MULTISIG(), force=True)
    gac_guardian = accounts.at(gac.WAR_ROOM_ACL(), force=True)

    # Focused on testing pausing functionality
    if gac.transferFromDisabled() == True:
        gac.enableTransferFrom({"from": gac_gov})

    # With the vault unpaused and GAC paused test all operations
    controller = interface.IController(vault_proxy.controller())
    strat = interface.IStrategy(controller.strategies(vault_proxy.token()))
    strat_gov = accounts.at(strat.governance(), force=True)
    if strat.paused():
        strat.unpause({"from": strat_gov})

    # Unpausing globally
    if gac.paused() == True:
        gac.unpause({"from": gac_gov})
        assert gac.paused() == False

    # Transfer funds from exploiters to user
    user = accounts[3]
    distribute_from_whales_realtime_percentage(user, 0.8, [vault_proxy.address])
    assert vault_proxy.balanceOf(user) > 0

    # Pausing globally from Guardian
    gac.pause({"from": gac_guardian})
    assert gac.paused() == True

    # Functions should revert due to global pause
    with brownie.reverts("Pausable: GAC Paused"):
        vault_proxy.earn({"from": governance})
    with brownie.reverts("Pausable: GAC Paused"):
        vault_proxy.withdraw(123, {"from": user})
    with brownie.reverts("Pausable: GAC Paused"):
        vault_proxy.withdrawAll({"from": user})
    with brownie.reverts("Pausable: GAC Paused"):
        vault_proxy.deposit(123, {"from": user})
    with brownie.reverts("Pausable: GAC Paused"):
        vault_proxy.depositAll({"from": user})
    with brownie.reverts("Pausable: GAC Paused"):
        vault_proxy.transfer(accounts[1], 123, {"from": user})
    with brownie.reverts("Pausable: GAC Paused"):
        vault_proxy.transferFrom(user, accounts[1], 123, {"from": accounts[1]})

    # Unpausing globally
    gac.unpause({"from": gac_gov})
    assert gac.paused() == False

    # Testing all operations

    ## Withdraw
    # bveCVX reverts on withdrawal
    if vault_proxy.address != "0xfd05D3C7fe2924020620A8bE4961bBaA747e6305":
        underlying = ERC20Upgradeable.at(vault_proxy.token())
        prev_balance_of_underlying = underlying.balanceOf(user)
        vault_proxy.withdraw(1000, {"from": user})
        assert underlying.balanceOf(user) > prev_balance_of_underlying
    else:
        # Distribute underlying to user
        underlying = ERC20Upgradeable.at(vault_proxy.token())
        distribute_from_whales_realtime_percentage(user, 0.8, [underlying.address])

    ## Deposit
    prev_shares = vault_proxy.balanceOf(user)
    prev_balance_of_underlying = underlying.balanceOf(user)
    underlying.approve(vault_proxy, underlying.balanceOf(user), {"from": user})
    vault_proxy.deposit(underlying.balanceOf(user) / 2, {"from": user})
    assert underlying.balanceOf(user) < prev_balance_of_underlying
    assert vault_proxy.balanceOf(user) > prev_shares

    ## DepositAll
    prev_shares = vault_proxy.balanceOf(user)
    prev_balance_of_underlying = underlying.balanceOf(user)
    vault_proxy.depositAll({"from": user})
    assert underlying.balanceOf(user) < prev_balance_of_underlying
    assert vault_proxy.balanceOf(user) > prev_shares

    # Earn
    # bharvestcrvRenBTC is broken
    if vault_proxy.address != "0xAf5A1DECfa95BAF63E0084a35c62592B774A2A87":
        prev_balance = vault_proxy.balance()
        vault_proxy.earn({"from": governance})
        assert vault_proxy.balance() == prev_balance

    ## Transfer From
    rando = accounts[1]
    amount = vault_proxy.balanceOf(user) / 4
    vault_proxy.approve(rando, vault_proxy.balanceOf(user), {"from": user})
    vault_proxy.transferFrom(user.address, rando.address, amount, {"from": rando})
    assert vault_proxy.balanceOf(rando.address) == amount

    # Transfer
    vault_proxy.transfer(accounts[2], amount, {"from": rando})
    assert vault_proxy.balanceOf(accounts[2]) == amount


@pytest.mark.parametrize(
    "settAddress",
    SETT_ADDRESSES_V1 + SETT_ADDRESSES_V1_1 + SETT_ADDRESSES_V4,
)
def test_gac_blacklist(settAddress, proxy_admin, proxy_admin_gov, bve_cvx, bcvx_crv):
    # UPGRADE block
    if settAddress in SETT_ADDRESSES_V1:
        vault_proxy = SettV1h.at(settAddress)
        governance = accounts.at(vault_proxy.governance(), force=True)

        new_vault_logic = SettV1h.deploy({"from": governance})

    elif settAddress in SETT_ADDRESSES_V1_1:
        vault_proxy = SettV1_1h.at(settAddress)
        governance = accounts.at(vault_proxy.governance(), force=True)

        new_vault_logic = SettV1_1h.deploy({"from": governance})
    else:
        vault_proxy = SettV4h.at(settAddress)
        governance = accounts.at(vault_proxy.governance(), force=True)

        new_vault_logic = SettV4h.deploy({"from": governance})

    if bve_cvx.paused() and not settAddress == bve_cvx.address:
        bve_gov = accounts.at(bve_cvx.governance(), force=True)
        bve_cvx.unpause({"from": bve_gov})

    if bcvx_crv.paused() and not settAddress == bcvx_crv.address:
        bcvx_crv_gov = accounts.at(bcvx_crv.governance(), force=True)
        bcvx_crv.unpause({"from": bcvx_crv_gov})

    # Execute upgrade
    proxy_admin.upgrade(vault_proxy, new_vault_logic, {"from": proxy_admin_gov})

    ## You can unpause if GAC is paused or unpaused (SettV1 can't be paused directly)
    try:
        if vault_proxy.paused() == True:
            vault_proxy.unpause({"from": governance})
            assert vault_proxy.paused() == False
    except:
        pass

    ## GAC Pause Block

    ## Get GAC actors
    gac = interface.IGac(vault_proxy.GAC())
    gac_gov = accounts.at(gac.DEV_MULTISIG(), force=True)

    # Unpausing globally
    if gac.paused():
        gac.unpause({"from": gac_gov})

    # Focused on testing pausing functionality
    if gac.transferFromDisabled():
        gac.enableTransferFrom({"from": gac_gov})

    ## GAC Blacklist Block

    # Define actors
    user = accounts[0]
    rando = accounts[1]
    want = interface.ERC20(vault_proxy.token())

    for exploiter in LIST_OF_EXPLOITERS:
        # Blacklist exploiters
        blacklisted_role = gac.BLACKLISTED_ROLE()
        gac.grantRole(blacklisted_role, exploiter, {"from": gac_gov})

        want_balance = want.balanceOf(exploiter)
        vault_balance = vault_proxy.balanceOf(exploiter)

        ## Should revert for exploiters
        with brownie.reverts("blacklisted"):
            vault_proxy.deposit(want_balance, {"from": exploiter})

        if settAddress in SETT_ADDRESSES_V4:
            with brownie.reverts("blacklisted"):
                vault_proxy.deposit(want_balance, [], {"from": exploiter})

        with brownie.reverts("blacklisted"):
            vault_proxy.depositAll({"from": exploiter})

        if settAddress in SETT_ADDRESSES_V4:
            with brownie.reverts("blacklisted"):
                vault_proxy.depositAll([], {"from": exploiter})

        if settAddress in [*SETT_ADDRESSES_V1, *SETT_ADDRESSES_V4]:
            with brownie.reverts("blacklisted"):
                vault_proxy.depositFor(rando, want_balance, {"from": exploiter})

            with brownie.reverts("blacklisted"):
                vault_proxy.depositFor(exploiter, want.balanceOf(user), {"from": user})

            if settAddress in SETT_ADDRESSES_V4:
                with brownie.reverts("blacklisted"):
                    vault_proxy.depositFor(rando, want_balance, [], {"from": exploiter})

                with brownie.reverts("blacklisted"):
                    vault_proxy.depositFor(
                        exploiter, want.balanceOf(user), [], {"from": user}
                    )

        with brownie.reverts("blacklisted"):
            vault_proxy.withdraw(vault_balance, {"from": exploiter})

        with brownie.reverts("blacklisted"):
            vault_proxy.withdrawAll({"from": exploiter})

        with brownie.reverts("blacklisted"):
            vault_proxy.transfer(rando, vault_balance, {"from": exploiter})

        with brownie.reverts("blacklisted"):
            vault_proxy.transfer(exploiter, vault_proxy.balanceOf(user), {"from": user})

        vault_proxy.approve(exploiter, MAX_UINT256, {"from": user})

        with brownie.reverts("blacklisted"):
            vault_proxy.transferFrom(
                user, rando, vault_proxy.balanceOf(user), {"from": exploiter}
            )

        vault_proxy.approve(rando, MAX_UINT256, {"from": user})

        with brownie.reverts("blacklisted"):
            vault_proxy.transferFrom(
                user, exploiter, vault_proxy.balanceOf(user), {"from": rando}
            )

        vault_proxy.approve(rando, MAX_UINT256, {"from": exploiter})

        with brownie.reverts("blacklisted"):
            vault_proxy.transferFrom(exploiter, rando, vault_balance, {"from": rando})

    ## No reverts for user
    want_balance = want.balanceOf(user)
    vault_balance = vault_proxy.balanceOf(user)

    vault_proxy.deposit(want_balance, {"from": user})

    if settAddress in SETT_ADDRESSES_V4:
        vault_proxy.deposit(want_balance, [], {"from": user})

    vault_proxy.depositAll({"from": user})

    if settAddress in SETT_ADDRESSES_V4:
        vault_proxy.depositAll([], {"from": user})

    if settAddress in [*SETT_ADDRESSES_V1, *SETT_ADDRESSES_V4]:
        vault_proxy.depositFor(rando, want_balance, {"from": user})

        if settAddress in SETT_ADDRESSES_V4:
            vault_proxy.depositFor(rando, want_balance, [], {"from": user})

    vault_proxy.withdraw(vault_balance, {"from": user})

    vault_proxy.withdrawAll({"from": user})

    vault_proxy.transfer(rando, vault_balance, {"from": user})

    vault_proxy.approve(rando, MAX_UINT256, {"from": user})
    vault_proxy.transferFrom(user, rando, vault_balance, {"from": rando})
