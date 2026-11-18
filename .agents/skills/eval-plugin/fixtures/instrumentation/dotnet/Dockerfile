# .NET, instrumented by Antithesis from /opt/antithesis/catalog.
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src
COPY . .
RUN dotnet publish -c Release -o /app

FROM mcr.microsoft.com/dotnet/runtime:8.0
COPY --from=build /app /app
RUN mkdir -p /opt/antithesis && ln -s /app /opt/antithesis/catalog
CMD ["dotnet", "/app/dotnetfixture.dll"]
