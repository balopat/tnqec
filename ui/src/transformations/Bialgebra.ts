import { DroppedLego, Connection, Operation } from '../types';
import { Z_REP_CODE, X_REP_CODE, getLegoStyle } from '../LegoStyles';
import _ from 'lodash';

export function canDoBialgebra(selectedLegos: DroppedLego[], connections: Connection[]): boolean {
    if (selectedLegos.length !== 2) return false;
    const [lego1, lego2] = selectedLegos;

    const lego_types = new Set([lego1.id, lego2.id]);
    if (!_.isEqual(lego_types, new Set([Z_REP_CODE, X_REP_CODE]))) {
        return false;
    }

    // Count connections between the two selected legos
    const connectionsBetween = connections.filter(conn => conn.containsLego(lego1.instanceId) && conn.containsLego(lego2.instanceId));
    // There should be exactly one connection between them
    return connectionsBetween.length === 1;
}

async function getDynamicLego(legoId: string, numLegs: number): Promise<DroppedLego> {
    const response = await fetch('/api/dynamiclego', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            lego_id: legoId,
            parameters: {
                d: numLegs
            }
        })
    });

    if (!response.ok) {
        throw new Error(`Failed to get dynamic lego: ${response.statusText}`);
    }

    const data = await response.json();
    return {
        ...data,
        instanceId: String("not set"),
        style: getLegoStyle(data.id, numLegs),
        x: 0,
        y: 0
    };
}

export async function applyBialgebra(legosToCommute: DroppedLego[], droppedLegos: DroppedLego[], connections: Connection[]): Promise<{
    connections: Connection[],
    droppedLegos: DroppedLego[],
    operation: Operation
}> {
    const [lego1, lego2] = legosToCommute;
    const connectionsBetween = connections.filter(conn => conn.containsLego(lego1.instanceId) && conn.containsLego(lego2.instanceId));
    const connectionsToLego1 = connections.filter(conn => conn.containsLego(lego1.instanceId) && !conn.containsLego(lego2.instanceId));
    const connectionsToLego2 = connections.filter(conn => conn.containsLego(lego2.instanceId) && !conn.containsLego(lego1.instanceId));

    const n_legs_lego1 = lego1.parity_check_matrix[0].length / 2;
    const n_legs_lego2 = lego2.parity_check_matrix[0].length / 2;

    // Determine which lego is Z and which is X
    const isLego1Z = lego1.id === Z_REP_CODE;
    const firstGroupType = isLego1Z ? X_REP_CODE : Z_REP_CODE;
    const secondGroupType = isLego1Z ? Z_REP_CODE : X_REP_CODE;

    // Create new legos for both groups
    const newLegos: DroppedLego[] = [];
    const newConnections: Connection[] = [];

    const n_group_1 = n_legs_lego1 - 1;
    const n_group_2 = n_legs_lego2 - 1;

    // Calculate required legs for each new lego
    // Each lego needs:
    // - n_legs_lego1 legs for connections to other legos in its group
    // - 1 leg for each external connection
    // - 1 leg for each dangling leg from the original lego
    const legsPerLego1 = n_group_2 + 1;
    const legsPerLego2 = n_group_1 + 1;

    // Get the maximum instance ID from existing legos
    const maxInstanceId = Math.max(...droppedLegos.map(l => parseInt(l.instanceId)));

    // Create first group of legos
    for (let i = 0; i < n_group_1; i++) {
        const baseLego = await getDynamicLego(firstGroupType, legsPerLego1);
        const newLego = {
            ...baseLego,
            instanceId: String(maxInstanceId + 1 + i),
            x: lego1.x + (i * 100), // Position them horizontally
            y: lego1.y
        };
        newLegos.push(newLego);
    }

    // Create second group of legos
    for (let i = 0; i < n_group_2; i++) {
        const baseLego = await getDynamicLego(secondGroupType, legsPerLego2);
        const newLego = {
            ...baseLego,
            instanceId: String(maxInstanceId + 1 + n_group_1 + i),
            x: lego2.x + (i * 100), // Position them horizontally
            y: lego2.y + 100 // Position them below the first group
        };
        newLegos.push(newLego);
    }

    // Create connections between the two groups
    for (let i = 0; i < n_group_1; i++) {
        for (let j = 0; j < n_group_2; j++) {
            newConnections.push(new Connection(
                {
                    legoId: newLegos[i].instanceId,
                    legIndex: j
                },
                {
                    legoId: newLegos[n_group_1 + j].instanceId,
                    legIndex: i
                }
            ));
        }
    }

    // Create connections for external legs
    connectionsToLego1.forEach((conn, index) => {
        const externalLegoId = conn.from.legoId === lego1.instanceId ? conn.to.legoId : conn.from.legoId;
        const externalLegIndex = conn.from.legoId === lego1.instanceId ? conn.to.legIndex : conn.from.legIndex;

        // Connect only one lego from the first group to each external lego
        newConnections.push(new Connection(
            {
                legoId: newLegos[index].instanceId,
                legIndex: n_group_2  // Always use the last leg index for external connections
            },
            { legoId: externalLegoId, legIndex: externalLegIndex }
        ));
    });

    // Create external connections for the second group
    connectionsToLego2.forEach((conn, index) => {
        const externalLegoId = conn.from.legoId === lego2.instanceId ? conn.to.legoId : conn.from.legoId;
        const externalLegIndex = conn.from.legoId === lego2.instanceId ? conn.to.legIndex : conn.from.legIndex;

        // Connect only one lego from the second group to each external lego
        newConnections.push(new Connection(
            {
                legoId: newLegos[n_group_1 + index].instanceId,
                legIndex: n_group_1  // Always use the last leg index for external connections
            },
            { legoId: externalLegoId, legIndex: externalLegIndex }
        ));
    });

    // Remove old legos and connections
    const updatedDroppedLegos = droppedLegos.filter(lego =>
        !legosToCommute.some(l => l.instanceId === lego.instanceId)
    ).concat(newLegos);

    const updatedConnections = connections.filter(conn =>
        !connectionsBetween.some(c =>
            c.from.legoId === conn.from.legoId &&
            c.from.legIndex === conn.from.legIndex &&
            c.to.legoId === conn.to.legoId &&
            c.to.legIndex === conn.to.legIndex
        ) &&
        !connectionsToLego1.some(c =>
            c.from.legoId === conn.from.legoId &&
            c.from.legIndex === conn.from.legIndex &&
            c.to.legoId === conn.to.legoId &&
            c.to.legIndex === conn.to.legIndex
        ) &&
        !connectionsToLego2.some(c =>
            c.from.legoId === conn.from.legoId &&
            c.from.legIndex === conn.from.legIndex &&
            c.to.legoId === conn.to.legoId &&
            c.to.legIndex === conn.to.legIndex
        )
    ).concat(newConnections);

    return {
        connections: updatedConnections,
        droppedLegos: updatedDroppedLegos,
        operation: {
            type: 'bialgebra',
            data: {
                legosToRemove: legosToCommute,
                connectionsToRemove: [...connectionsBetween, ...connectionsToLego1, ...connectionsToLego2],
                legosToAdd: newLegos,
                connectionsToAdd: newConnections
            }
        }
    };
}
