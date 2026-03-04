import asyncio
import grpc
from work_ticket_emulator.grpc import (
    work_ticket_pb2,
    work_ticket_pb2_grpc,
    location_pb2,
    location_pb2_grpc,
    product_pb2,
    product_pb2_grpc,
    common_pb2,
)


async def run():
    async with grpc.aio.insecure_channel("localhost:50052") as channel:
        ticket_stub = work_ticket_pb2_grpc.WorkTicketServiceStub(channel)
        location_stub = location_pb2_grpc.LocationServiceStub(channel)
        product_stub = product_pb2_grpc.ProductServiceStub(channel)

        # Test GetWorkTicket
        print("--- Testing GetWorkTicket ---")
        try:
            response = await ticket_stub.GetWorkTicket(
                work_ticket_pb2.GetWorkTicketRequest(responseid="3856498")
            )
            print(f"Ticket responseid: '{response.responseid}'")
            print(f"Product Brand: '{response.product.brand_ops}'")
            print(f"Location Country: '{response.location.country_name_ops}'")
        except grpc.RpcError as e:
            print(f"Failed to get ticket: {e.details()}")

        # Test ListWorkTickets
        print("\n--- Testing ListWorkTickets ---")
        try:
            response = await ticket_stub.ListWorkTickets(
                work_ticket_pb2.ListWorkTicketsRequest(
                    query="FRANCE",
                    pagination=common_pb2.PaginationRequest(page=1, page_size=2),
                )
            )
            print(
                f"Found total {response.pagination.total} matching tickets. Page {response.pagination.page} contains {len(response.items)} items."
            )
            for t in response.items:
                print(
                    f"- Ticket: '{t.responseid}' Location: '{t.location.country_name_ops}'"
                )
        except grpc.RpcError as e:
            print(f"Failed to list tickets: {e.details()}")

        # Test Location Service
        print("\n--- Testing ListLocations ---")
        try:
            response = await location_stub.ListLocations(
                location_pb2.ListLocationsRequest(
                    query="GERMANY",
                    pagination=common_pb2.PaginationRequest(page=1, page_size=2),
                )
            )
            print(
                f"Found total {response.pagination.total} matching locations. Page {response.pagination.page} contains {len(response.items)} items."
            )
            for t in response.items:
                print(
                    f"- [ID: {t.id}] Location: '{t.country_name_ops}' Region: '{t.px_region}'"
                )
        except grpc.RpcError as e:
            print(f"Failed to search locations: {e.details()}")

        # Test Product Service
        print("\n--- Testing ListProducts ---")
        try:
            response = await product_stub.ListProducts(
                product_pb2.ListProductsRequest(
                    query="THINK",
                    pagination=common_pb2.PaginationRequest(page=1, page_size=3),
                )
            )
            print(
                f"Found total {response.pagination.total} matching products. Page {response.pagination.page} contains {len(response.items)} items."
            )
            for t in response.items:
                print(
                    f"- [ID: {t.id}] Product Brand: '{t.brand_ops}' Group: '{t.product_group_ops}'"
                )
        except grpc.RpcError as e:
            print(f"Failed to search products: {e.details()}")


if __name__ == "__main__":
    asyncio.run(run())
