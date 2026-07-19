# Container definitions

All custom containers used in the system for benchmarking.

## Core

The BPMN workflow engine, a custom configured and extended version of [`operaton`](https://operaton.org/)

## Infrastructure

These containers are everything that is part of the communication channel that is not
the engine or target microservice.

## Logging

This container runs the benchmark by firing events and measuring relevant network parameters.
It consolidates logs and outputs raw data for analysis.

## Services

Sinks for engine communication. These conatiners speak the required protocols and react like
real microservices would except that they do not have any real buisiness logic outside of the
communication IO.