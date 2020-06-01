from server.methods.transaction import Transaction
from server.methods.address import Address
from server.methods.general import General
from server.methods.esplora import Esplora
from server.methods.block import Block
from flask import Response, Blueprint
from flask_restful import Resource
from server import stats
import config

blueprint = Blueprint("esplora", __name__)

@stats.rest
@blueprint.route("/esplora/block/<string:bhash>", methods=["GET"])
def block_hash(bhash):
    data = Block().hash(bhash)

    if data["error"] is None:
        result = data["result"]
        return Esplora().block(result)

    else:
        return Response("Block not found", mimetype="text/plain", status=404)

class EsploraBlockByHashStatus(Resource):
    @stats.rest
    def get(self, bhash):
        data = Block().hash(bhash)
        next_best = None
        height = None
        best = False

        if data["error"] is None:
            result = data["result"]
            next_best = result["nextblockhash"]
            height = result["height"]
            best = True

        return {
            "in_best_chain": best,
            "height": height,
            "next_best": next_best
        }

class EsploraBlockByHashTransactions(Resource):
    @stats.rest
    def get(self, bhash, start=0):
        data = Block().hash(bhash)
        transactions = []

        if start % config.tx_page != 0:
            return Response(f"start index must be a multipication of {config.tx_page}", mimetype="text/plain", status=400)

        if data["error"] is None:
            result = data["result"]

            for thash in result["tx"][start:start + config.tx_page]:
                transaction = Transaction().info(thash)["result"]
                transactions.append(Esplora().transaction(transaction))

            return transactions

        else:
            return Response("Block not found", mimetype="text/plain", status=404)

class EsploraTransactionInfo(Resource):
    @stats.rest
    def get(self, thash):
        data = Transaction().info(thash)

        if data["error"] is None:
            result = data["result"]
            return Esplora().transaction(result)

        else:
            return Response("Transaction not found", mimetype="text/plain", status=404)

class EsploraAddressInfo(Resource):
    @stats.rest
    def get(self, address):
        data = Address().history(address)

        if data["error"] is None:
            result = data["result"]
            mempool = data = Address().mempool(address)["result"]
            balance = data = Address().balance(address)["result"]

            # ToDo: Fix transactions count here

            return {
                "address": address,
                "chain_stats": {
                    "funded_txo_count": 0,
                    "funded_txo_sum": balance["received"],
                    "spent_txo_count": 0,
                    "spent_txo_sum": balance["received"] - balance["balance"],
                    "tx_count": result["txcount"]
                },
                "mempool_stats": {
                    "funded_txo_count": 0,
                    "funded_txo_sum": 0,
                    "spent_txo_count": 0,
                    "spent_txo_sum": 0,
                    "tx_count": mempool["txcount"]
                }
            }

        else:
            return Response("Invalid Bitcoin address", mimetype="text/plain", status=400)

class EsploraAddressTransactions(Resource):
    @stats.rest
    def get(self, address):
        data = Address().history(address)
        transactions = []

        if data["error"] is None:
            result = data["result"]

            for thash in result["tx"][0:config.tx_page]:
                transaction = Transaction().info(thash)["result"]
                transactions.append(Esplora().transaction(transaction))

            return transactions

        else:
            return Response("Invalid Bitcoin address", mimetype="text/plain", status=400)

class EsploraAddressTransactionsSkipHash(Resource):
    @stats.rest
    def get(self, address, thash):
        data = Address().history(address)
        transactions = []
        start = 0

        if data["error"] is None:
            result = data["result"]

            if thash in result["tx"]:
                start = result["tx"].index(thash) + 1

            for thash in result["tx"][start:start + config.tx_page]:
                transaction = Transaction().info(thash)["result"]
                transactions.append(Esplora().transaction(transaction))

            return transactions

        else:
            return Response("Invalid Bitcoin address", mimetype="text/plain", status=400)

class EsploraBlocksRangeStart(Resource):
    @stats.rest
    def get(self):
        data = General().info()
        height = data["result"]["blocks"]
        blocks = []

        data = Block().range(height, config.block_page)

        for block in data:
            blocks.append(Esplora().block(block))

        return blocks

class EsploraBlocksRange(Resource):
    @stats.rest
    def get(self, height):
        data = General().info()
        blocks = []

        data = Block().range(height, config.block_page)

        for block in data:
            blocks.append(Esplora().block(block))

        return blocks

class EsploraPlainBlockHash(Resource):
    @stats.rest
    def get(self, height):
        data = Block().height(height)

        if data["error"] is None:
            return Response(data["result"]["hash"], mimetype="text/plain")

        else:
            return Response("Block not found", mimetype="text/plain", status=404)

class EsploraPlainTipHeight(Resource):
    @stats.rest
    def get(self):
        data = General().info()
        return Response(str(data["result"]["blocks"]), mimetype="text/plain")

def init(api, app):
    api.add_resource(EsploraBlockByHashStatus, "/esplora/block/<string:bhash>/status")
    api.add_resource(EsploraBlockByHashTransactions, "/esplora/block/<string:bhash>/txs/<int:start>")

    api.add_resource(EsploraTransactionInfo, "/esplora/tx/<string:thash>")
    api.add_resource(EsploraPlainBlockHash, "/esplora/block-height/<int:height>")
    api.add_resource(EsploraPlainTipHeight, "/esplora/blocks/tip/height")

    api.add_resource(EsploraAddressInfo, "/esplora/address/<string:address>")
    api.add_resource(EsploraAddressTransactions, "/esplora/address/<string:address>/txs")
    api.add_resource(EsploraAddressTransactionsSkipHash, "/esplora/address/<string:address>/txs/chain/<string:thash>")

    api.add_resource(EsploraBlocksRangeStart, "/esplora/blocks")
    api.add_resource(EsploraBlocksRange, "/esplora/blocks/<int:height>")

    app.register_blueprint(blueprint)
